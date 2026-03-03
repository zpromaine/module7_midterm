import datetime
from pathlib import Path
import pandas as pd
import pytest
from unittest.mock import Mock, patch, PropertyMock
from decimal import Decimal
from tempfile import TemporaryDirectory
from app.calculator import Calculator
from app.calculator_repl import calculator_repl
from app.calculator_config import CalculatorConfig
from app.exceptions import OperationError, ValidationError
from app.history import LoggingObserver, AutoSaveObserver
from app.operations import OperationFactory

# Fixture to initialize Calculator with a temporary directory for file paths
@pytest.fixture
def calculator():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config = CalculatorConfig(base_dir=temp_path)

        # Patch properties to use the temporary directory paths
        with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
             patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file, \
             patch.object(CalculatorConfig, 'history_dir', new_callable=PropertyMock) as mock_history_dir, \
             patch.object(CalculatorConfig, 'history_file', new_callable=PropertyMock) as mock_history_file:
            
            # Set return values to use paths within the temporary directory
            mock_log_dir.return_value = temp_path / "logs"
            mock_log_file.return_value = temp_path / "logs/calculator.log"
            mock_history_dir.return_value = temp_path / "history"
            mock_history_file.return_value = temp_path / "history/calculator_history.csv"
            
            # Return an instance of Calculator with the mocked config
            yield Calculator(config=config)

# Test Calculator Initialization

def test_calculator_initialization(calculator):
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []
    assert calculator.operation_strategy is None

# Test Logging Setup

@patch('app.calculator.logging.info')
def test_logging_setup(logging_info_mock):
    with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
         patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file:
        mock_log_dir.return_value = Path('/tmp/logs')
        mock_log_file.return_value = Path('/tmp/logs/calculator.log')
        
        # Instantiate calculator to trigger logging
        calculator = Calculator(CalculatorConfig())
        logging_info_mock.assert_any_call("Calculator initialized with configuration")

# Test Adding and Removing Observers

def test_add_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    assert observer in calculator.observers

def test_remove_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    calculator.remove_observer(observer)
    assert observer not in calculator.observers

# Test Setting Operations

def test_set_operation(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    assert calculator.operation_strategy == operation

# Test Performing Operations

def test_perform_operation_addition(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    result = calculator.perform_operation(2, 3)
    assert result == Decimal('5')

def test_perform_operation_validation_error(calculator):
    calculator.set_operation(OperationFactory.create_operation('add'))
    with pytest.raises(ValidationError):
        calculator.perform_operation('invalid', 3)

def test_perform_operation_operation_error(calculator):
    with pytest.raises(OperationError, match="No operation set"):
        calculator.perform_operation(2, 3)

# Test Undo/Redo Functionality

def test_undo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    assert calculator.history == []

def test_redo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    calculator.redo()
    assert len(calculator.history) == 1

# Test History Management

@patch('app.calculator.pd.DataFrame.to_csv')
def test_save_history(mock_to_csv, calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.save_history()
    mock_to_csv.assert_called_once()

@patch('app.calculator.pd.read_csv')
@patch('app.calculator.Path.exists', return_value=True)
def test_load_history(mock_exists, mock_read_csv, calculator):
    # Mock CSV data to match the expected format in from_dict
    mock_read_csv.return_value = pd.DataFrame({
        'operation': ['Addition'],
        'operand1': ['2'],
        'operand2': ['3'],
        'result': ['5'],
        'timestamp': [datetime.datetime.now().isoformat()]
    })
    
    # Test the load_history functionality
    try:
        calculator.load_history()
        # Verify history length after loading
        assert len(calculator.history) == 1
        # Verify the loaded values
        assert calculator.history[0].operation == "Addition"
        assert calculator.history[0].operand1 == Decimal("2")
        assert calculator.history[0].operand2 == Decimal("3")
        assert calculator.history[0].result == Decimal("5")
    except OperationError:
        pytest.fail("Loading history failed due to OperationError")
        
            
# Test Clearing History

def test_clear_history(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.clear_history()
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []

# Test REPL Commands (using patches for input/output handling)

@patch('builtins.input', side_effect=['exit'])
@patch('builtins.print')
def test_calculator_repl_exit(mock_print, mock_input):
    with patch('app.calculator.Calculator.save_history') as mock_save_history:
        calculator_repl()
        mock_save_history.assert_called_once()
        mock_print.assert_any_call("History saved successfully.")
        mock_print.assert_any_call("Goodbye!")

@patch('builtins.input', side_effect=['help', 'exit'])
@patch('builtins.print')
def test_calculator_repl_help(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("\nAvailable commands:")

@patch('builtins.input', side_effect=['add', '2', '3', 'exit'])
@patch('builtins.print')
def test_calculator_repl_addition(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("\nResult: 5")

# Additional tests to improve coverage

# Test undo with nothing to undo
def test_undo_empty(calculator):
    result = calculator.undo()
    assert result == False

# Test redo with nothing to redo
def test_redo_empty(calculator):
    result = calculator.redo()
    assert result == False

# Test notify_observers
def test_notify_observers(calculator):
    mock_observer = Mock()
    calculator.add_observer(mock_observer)
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    mock_observer.update.assert_called_once()

# Test save_history with empty history
@patch('app.calculator.pd.DataFrame.to_csv')
def test_save_empty_history(mock_to_csv, calculator):
    calculator.save_history()
    mock_to_csv.assert_called_once()

# Test get_history_dataframe
def test_get_history_dataframe(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    df = calculator.get_history_dataframe()
    assert len(df) == 1
    assert df.iloc[0]['operation'] == 'Addition'

# Test show_history
def test_show_history(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    history = calculator.show_history()
    assert len(history) == 1
    assert 'Addition' in history[0]

# Test REPL history command
@patch('builtins.input', side_effect=['history', 'exit'])
@patch('builtins.print')
@patch('app.calculator.Calculator.load_history')
@patch('app.calculator.Calculator.show_history', return_value=[])
def test_calculator_repl_history_empty(mock_show, mock_load, mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("No calculations in history")

# Test REPL history command with entries
@patch('builtins.input', side_effect=['add', '2', '3', 'history', 'exit'])
@patch('builtins.print')
def test_calculator_repl_history_with_entries(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("\nCalculation History:")

# Test REPL clear command
@patch('builtins.input', side_effect=['clear', 'exit'])
@patch('builtins.print')
def test_calculator_repl_clear(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("History cleared")

# Test REPL undo command
@patch('builtins.input', side_effect=['undo', 'exit'])
@patch('builtins.print')
def test_calculator_repl_undo(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("Nothing to undo")

# Test REPL redo command
@patch('builtins.input', side_effect=['redo', 'exit'])
@patch('builtins.print')
def test_calculator_repl_redo(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("Nothing to redo")

# Test REPL save command
@patch('builtins.input', side_effect=['save', 'exit'])
@patch('builtins.print')
def test_calculator_repl_save(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("History saved successfully")

# Test REPL load command
@patch('builtins.input', side_effect=['load', 'exit'])
@patch('builtins.print')
def test_calculator_repl_load(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("History loaded successfully")

# Test REPL unknown command
@patch('builtins.input', side_effect=['unknown', 'exit'])
@patch('builtins.print')
def test_calculator_repl_unknown_command(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("Unknown command: 'unknown'. Type 'help' for available commands.")

# Test REPL cancel first input
@patch('builtins.input', side_effect=['add', 'cancel', 'exit'])
@patch('builtins.print')
def test_calculator_repl_cancel_first_input(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("Operation cancelled")

# Test REPL cancel second input
@patch('builtins.input', side_effect=['add', '2', 'cancel', 'exit'])
@patch('builtins.print')
def test_calculator_repl_cancel_second_input(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("Operation cancelled")

# Test REPL division by zero error
@patch('builtins.input', side_effect=['divide', '5', '0', 'exit'])
@patch('builtins.print')
def test_calculator_repl_division_by_zero(mock_print, mock_input):
    calculator_repl()
    printed = [str(call) for call in mock_print.call_args_list]
    assert any('Error' in p for p in printed)

# Test CalculatorMemento to_dict and from_dict
def test_memento_to_dict_from_dict(calculator):
    from app.calculator_memento import CalculatorMemento
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    memento = CalculatorMemento(calculator.history.copy())
    data = memento.to_dict()
    restored = CalculatorMemento.from_dict(data)
    assert len(restored.history) == 1
    assert restored.history[0].operation == 'Addition'


# Tests to push coverage over 90%

# calculator.py line 57-59: load_history warning on init
def test_calculator_load_history_warning_on_init():
    with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
         patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file, \
         patch.object(CalculatorConfig, 'history_dir', new_callable=PropertyMock) as mock_history_dir, \
         patch.object(CalculatorConfig, 'history_file', new_callable=PropertyMock) as mock_history_file:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_log_dir.return_value = temp_path / "logs"
            mock_log_file.return_value = temp_path / "logs/calculator.log"
            mock_history_dir.return_value = temp_path / "history"
            mock_history_file.return_value = temp_path / "history/calculator_history.csv"
            with patch('app.calculator.Calculator.load_history', side_effect=Exception("load error")):
                calc = Calculator()
                assert calc.history == []

# calculator.py line 83-86: logging setup error
def test_calculator_logging_setup_error():
    with patch('app.calculator.logging.basicConfig', side_effect=Exception("log error")):
        with pytest.raises(Exception, match="log error"):
            with TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                config = CalculatorConfig(base_dir=temp_path)
                Calculator(config=config)

# calculator.py line 199: max history size exceeded
def test_max_history_size(calculator):
    calculator.config.max_history_size = 2
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(1, 1)
    calculator.perform_operation(2, 2)
    calculator.perform_operation(3, 3)
    assert len(calculator.history) == 2

# calculator.py line 210-213: perform_operation generic exception
def test_perform_operation_generic_exception(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    with patch.object(operation, 'execute', side_effect=Exception("unexpected")):
        with pytest.raises(OperationError, match="Operation failed"):
            calculator.perform_operation(2, 3)

# calculator_config.py lines 104, 106, 108: validate errors
def test_config_validate_invalid_history_size():
    from app.exceptions import ConfigurationError
    with TemporaryDirectory() as temp_dir:
        config = CalculatorConfig(base_dir=Path(temp_dir))
        config.max_history_size = -1
        with pytest.raises(ConfigurationError):
            config.validate()

def test_config_validate_invalid_precision():
    from app.exceptions import ConfigurationError
    with TemporaryDirectory() as temp_dir:
        config = CalculatorConfig(base_dir=Path(temp_dir))
        config.precision = -1
        with pytest.raises(ConfigurationError):
            config.validate()

# history.py line 51: LoggingObserver with None
def test_logging_observer_none():
    from app.history import LoggingObserver
    observer = LoggingObserver()
    with pytest.raises(AttributeError):
        observer.update(None)

# history.py line 80: AutoSaveObserver invalid calculator
def test_auto_save_observer_invalid_calculator():
    from app.history import AutoSaveObserver
    with pytest.raises(TypeError):
        AutoSaveObserver(object())

# history.py line 94: AutoSaveObserver with None
def test_auto_save_observer_none_calculation(calculator):
    from app.history import AutoSaveObserver
    observer = AutoSaveObserver(calculator)
    with pytest.raises(AttributeError):
        observer.update(None)

# input_validators.py line 31: value exceeds max
def test_input_validator_exceeds_max():
    from app.input_validators import InputValidator
    config = CalculatorConfig()
    config.max_input_value = Decimal('10')
    with pytest.raises(ValidationError, match="exceeds maximum"):
        InputValidator.validate_number('999', config)

# calculator_repl.py lines 45-46: save history error on exit
@patch('builtins.input', side_effect=['exit'])
@patch('builtins.print')
def test_calculator_repl_exit_save_error(mock_print, mock_input):
    with patch('app.calculator.Calculator.save_history', side_effect=Exception("save error")):
        calculator_repl()
        mock_print.assert_any_call("Warning: Could not save history: save error")

# calculator_repl.py lines 88-89, 97-98: undo/redo with history
@patch('builtins.input', side_effect=['add', '2', '3', 'undo', 'redo', 'exit'])
@patch('builtins.print')
def test_calculator_repl_undo_redo_with_history(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("Operation undone")
    mock_print.assert_any_call("Operation redone")

# calculator_repl.py lines 129-131: save error in repl
@patch('builtins.input', side_effect=['save', 'exit'])
@patch('builtins.print')
def test_calculator_repl_save_error(mock_print, mock_input):
    with patch('app.calculator.Calculator.save_history', side_effect=Exception("save error")):
        calculator_repl()
        mock_print.assert_any_call("Error saving history: save error")

# calculator_repl.py lines 137-154: load error in repl
@patch('builtins.input', side_effect=['load', 'exit'])
@patch('builtins.print')
def test_calculator_repl_load_error(mock_print, mock_input):
    with patch('app.calculator.Calculator.load_history', side_effect=Exception("load error")):
        calculator_repl()
        mock_print.assert_any_call("Error loading history: load error")
