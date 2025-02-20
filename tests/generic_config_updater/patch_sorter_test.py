import jsonpatch
import unittest
from unittest.mock import MagicMock, Mock

import generic_config_updater.patch_sorter as ps
from .gutest_helpers import Files, create_side_effect_dict
from generic_config_updater.gu_common import ConfigWrapper, PatchWrapper, OperationWrapper, \
                                             GenericConfigUpdaterError, OperationType, JsonChange, PathAddressing

class TestDiff(unittest.TestCase):
    def test_apply_move__updates_current_config(self):
        # Arrange
        diff = ps.Diff(current_config=Files.CROPPED_CONFIG_DB_AS_JSON, target_config=Files.ANY_CONFIG_DB)
        move = ps.JsonMove.from_patch(Files.SINGLE_OPERATION_CONFIG_DB_PATCH)

        expected = ps.Diff(current_config=Files.CONFIG_DB_AFTER_SINGLE_OPERATION, target_config=Files.ANY_CONFIG_DB)

        # Act
        actual = diff.apply_move(move)

        # Assert
        self.assertEqual(expected.current_config, actual.current_config)
        self.assertEqual(expected.target_config, actual.target_config)

    def test_has_no_diff__diff_exists__returns_false(self):
        # Arrange
        diff = ps.Diff(current_config=Files.CROPPED_CONFIG_DB_AS_JSON,
                       target_config=Files.CONFIG_DB_AFTER_SINGLE_OPERATION)

        # Act and Assert
        self.assertFalse(diff.has_no_diff())

    def test_has_no_diff__no_diff__returns_true(self):
        # Arrange
        diff = ps.Diff(current_config=Files.CROPPED_CONFIG_DB_AS_JSON,
                       target_config=Files.CROPPED_CONFIG_DB_AS_JSON)

        # Act and Assert
        self.assertTrue(diff.has_no_diff())

    def test_hash__different_current_config__different_hashes(self):
        # Arrange
        diff1 = ps.Diff(current_config=Files.CROPPED_CONFIG_DB_AS_JSON, target_config=Files.ANY_CONFIG_DB)
        diff2 = ps.Diff(current_config=Files.CROPPED_CONFIG_DB_AS_JSON, target_config=Files.ANY_CONFIG_DB)
        diff3 = ps.Diff(current_config=Files.CONFIG_DB_AFTER_SINGLE_OPERATION, target_config=Files.ANY_CONFIG_DB)

        # Act
        hash1 = hash(diff1)
        hash2 = hash(diff2)
        hash3 = hash(diff3)

        # Assert
        self.assertEqual(hash1, hash2) # same current config
        self.assertNotEqual(hash1, hash3)

    def test_hash__different_target_config__different_hashes(self):
        # Arrange
        diff1 = ps.Diff(current_config=Files.ANY_CONFIG_DB, target_config=Files.CROPPED_CONFIG_DB_AS_JSON)
        diff2 = ps.Diff(current_config=Files.ANY_CONFIG_DB, target_config=Files.CROPPED_CONFIG_DB_AS_JSON)
        diff3 = ps.Diff(current_config=Files.ANY_CONFIG_DB, target_config=Files.CONFIG_DB_AFTER_SINGLE_OPERATION)

        # Act
        hash1 = hash(diff1)
        hash2 = hash(diff2)
        hash3 = hash(diff3)

        # Assert
        self.assertEqual(hash1, hash2) # same target config
        self.assertNotEqual(hash1, hash3)

    def test_hash__swapped_current_and_target_configs__different_hashes(self):
        # Arrange
        diff1 = ps.Diff(current_config=Files.ANY_CONFIG_DB, target_config=Files.ANY_OTHER_CONFIG_DB)
        diff2 = ps.Diff(current_config=Files.ANY_OTHER_CONFIG_DB, target_config=Files.ANY_CONFIG_DB)

        # Act
        hash1 = hash(diff1)
        hash2 = hash(diff2)

        # Assert
        self.assertNotEqual(hash1, hash2)

    def test_eq__different_current_config__returns_false(self):
        # Arrange
        diff = ps.Diff(Files.ANY_CONFIG_DB, Files.ANY_CONFIG_DB)
        other_diff = ps.Diff(Files.ANY_OTHER_CONFIG_DB, Files.ANY_CONFIG_DB)

        # Act and assert
        self.assertNotEqual(diff, other_diff)
        self.assertFalse(diff == other_diff)

    def test_eq__different_target_config__returns_false(self):
        # Arrange
        diff = ps.Diff(Files.ANY_CONFIG_DB, Files.ANY_CONFIG_DB)
        other_diff = ps.Diff(Files.ANY_CONFIG_DB, Files.ANY_OTHER_CONFIG_DB)

        # Act and assert
        self.assertNotEqual(diff, other_diff)
        self.assertFalse(diff == other_diff)

    def test_eq__different_target_config__returns_true(self):
        # Arrange
        diff = ps.Diff(Files.ANY_CONFIG_DB, Files.ANY_CONFIG_DB)
        other_diff = ps.Diff(Files.ANY_CONFIG_DB, Files.ANY_CONFIG_DB)

        # Act and assert
        self.assertEqual(diff, other_diff)
        self.assertTrue(diff == other_diff)

class TestJsonMove(unittest.TestCase):
    def setUp(self):
        self.operation_wrapper = OperationWrapper()
        self.any_op_type = OperationType.REPLACE
        self.any_tokens = ["table1", "key11"]
        self.any_path = "/table1/key11"
        self.any_config = {
            "table1": {
                "key11": "value11"
            }
        }
        self.any_value = "value11"
        self.any_operation = self.operation_wrapper.create(self.any_op_type, self.any_path, self.any_value)
        self.any_diff = ps.Diff(self.any_config, self.any_config)

    def test_ctor__delete_op_whole_config__none_value_and_empty_path(self):
        # Arrange
        path = ""
        diff = ps.Diff(current_config={}, target_config=self.any_config)

        # Act
        jsonmove = ps.JsonMove(diff, OperationType.REMOVE, [])

        # Assert
        self.verify_jsonmove(self.operation_wrapper.create(OperationType.REMOVE, path),
                             OperationType.REMOVE,
                             [],
                             None,
                             jsonmove)
    def test_ctor__remove_op__operation_created_directly(self):
        # Arrange and Act
        jsonmove = ps.JsonMove(self.any_diff, OperationType.REMOVE, self.any_tokens)

        # Assert
        self.verify_jsonmove(self.operation_wrapper.create(OperationType.REMOVE, self.any_path),
                             OperationType.REMOVE,
                             self.any_tokens,
                             None,
                             jsonmove)

    def test_ctor__replace_op_whole_config__whole_config_value_and_empty_path(self):
        # Arrange
        path = ""
        diff = ps.Diff(current_config={}, target_config=self.any_config)

        # Act
        jsonmove = ps.JsonMove(diff, OperationType.REPLACE, [], [])

        # Assert
        self.verify_jsonmove(self.operation_wrapper.create(OperationType.REPLACE, path, self.any_config),
                             OperationType.REPLACE,
                             [],
                             [],
                             jsonmove)

    def test_ctor__replace_op__operation_created_directly(self):
        # Arrange and Act
        jsonmove = ps.JsonMove(self.any_diff, OperationType.REPLACE, self.any_tokens, self.any_tokens)

        # Assert
        self.verify_jsonmove(self.operation_wrapper.create(OperationType.REPLACE, self.any_path, self.any_value),
                             OperationType.REPLACE,
                             self.any_tokens,
                             self.any_tokens,
                             jsonmove)

    def test_ctor__add_op_whole_config__whole_config_value_and_empty_path(self):
        # Arrange
        path = ""
        diff = ps.Diff(current_config={}, target_config=self.any_config)

        # Act
        jsonmove = ps.JsonMove(diff, OperationType.ADD, [], [])

        # Assert
        self.verify_jsonmove(self.operation_wrapper.create(OperationType.ADD, path, self.any_config),
                             OperationType.ADD,
                             [],
                             [],
                             jsonmove)

    def test_ctor__add_op_path_exist__same_value_and_path(self):
        # Arrange and Act
        jsonmove = ps.JsonMove(self.any_diff, OperationType.ADD, self.any_tokens, self.any_tokens)

        # Assert
        self.verify_jsonmove(self.operation_wrapper.create(OperationType.ADD, self.any_path, self.any_value),
                             OperationType.ADD,
                             self.any_tokens,
                             self.any_tokens,
                             jsonmove)

    def test_ctor__add_op_path_exist_include_list__same_value_and_path(self):
        # Arrange
        current_config = {
            "table1": {
                "list1": ["value11", "value13"]
            }
        }
        target_config = {
            "table1": {
                "list1": ["value11", "value12", "value13", "value14"]
            }
        }
        diff = ps.Diff(current_config, target_config)
        op_type = OperationType.ADD
        current_config_tokens = ["table1", "list1", 1] # Index is 1 which does not exist in target
        target_config_tokens = ["table1", "list1", 1]
        expected_jsonpatch_path = "/table1/list1/1"
        expected_jsonpatch_value = "value12"
        # NOTE: the target config can contain more diff than the given move.

        # Act
        jsonmove = ps.JsonMove(diff, op_type, current_config_tokens, target_config_tokens)

        # Assert
        self.verify_jsonmove(self.operation_wrapper.create(op_type, expected_jsonpatch_path, expected_jsonpatch_value),
                             op_type,
                             current_config_tokens,
                             target_config_tokens,
                             jsonmove)

    def test_ctor__add_op_path_exist_list_index_doesnot_exist_in_target___same_value_and_path(self):
        # Arrange
        current_config = {
            "table1": {
                "list1": ["value11"]
            }
        }
        target_config = {
            "table1": {
                "list1": ["value12"]
            }
        }
        diff = ps.Diff(current_config, target_config)
        op_type = OperationType.ADD
        current_config_tokens = ["table1", "list1", 1] # Index is 1 which does not exist in target
        target_config_tokens = ["table1", "list1", 0]
        expected_jsonpatch_path = "/table1/list1/1"
        expected_jsonpatch_value = "value12"
        # NOTE: the target config can contain more diff than the given move.

        # Act
        jsonmove = ps.JsonMove(diff, op_type, current_config_tokens, target_config_tokens)

        # Assert
        self.verify_jsonmove(self.operation_wrapper.create(op_type, expected_jsonpatch_path, expected_jsonpatch_value),
                             op_type,
                             current_config_tokens,
                             target_config_tokens,
                             jsonmove)

    def test_ctor__add_op_path_doesnot_exist__value_and_path_of_parent(self):
        # Arrange
        current_config = {
        }
        target_config = {
            "table1": {
                "key11": {
                    "key111": "value111"
                }
            }
        }
        diff = ps.Diff(current_config, target_config)
        op_type = OperationType.ADD
        current_config_tokens = ["table1", "key11", "key111"]
        target_config_tokens = ["table1", "key11", "key111"]
        expected_jsonpatch_path = "/table1"
        expected_jsonpatch_value = {
            "key11": {
                "key111": "value111"
            }
        }
        # NOTE: the target config can contain more diff than the given move.

        # Act
        jsonmove = ps.JsonMove(diff, op_type, current_config_tokens, target_config_tokens)

        # Assert
        self.verify_jsonmove(self.operation_wrapper.create(op_type, expected_jsonpatch_path, expected_jsonpatch_value),
                             op_type,
                             current_config_tokens,
                             target_config_tokens,
                             jsonmove)

    def test_ctor__add_op_path_doesnot_exist_include_list__value_and_path_of_parent(self):
        # Arrange
        current_config = {
        }
        target_config = {
            "table1": {
                "list1": ["value11", "value12", "value13", "value14"]
            }
        }
        diff = ps.Diff(current_config, target_config)
        op_type = OperationType.ADD
        current_config_tokens = ["table1", "list1", 0]
        target_config_tokens = ["table1", "list1", 1]
        expected_jsonpatch_path = "/table1"
        expected_jsonpatch_value = {
            "list1": ["value12"]
        }
        # NOTE: the target config can contain more diff than the given move.

        # Act
        jsonmove = ps.JsonMove(diff, op_type, current_config_tokens, target_config_tokens)

        # Assert
        self.verify_jsonmove(self.operation_wrapper.create(op_type, expected_jsonpatch_path, expected_jsonpatch_value),
                             op_type,
                             current_config_tokens,
                             target_config_tokens,
                             jsonmove)

    def test_from_patch__more_than_1_op__failure(self):
        # Arrange
        patch = jsonpatch.JsonPatch([self.any_operation, self.any_operation])

        # Act and Assert
        self.assertRaises(GenericConfigUpdaterError, ps.JsonMove.from_patch, patch)

    def test_from_patch__delete_op__delete_jsonmove(self):
        # Arrange
        operation = self.operation_wrapper.create(OperationType.REMOVE, self.any_path)
        patch = jsonpatch.JsonPatch([operation])

        # Act
        jsonmove = ps.JsonMove.from_patch(patch)

        # Assert
        self.verify_jsonmove(operation,
                             OperationType.REMOVE,
                             self.any_tokens,
                             None,
                             jsonmove)

    def test_from_patch__replace_op__replace_jsonmove(self):
        # Arrange
        operation = self.operation_wrapper.create(OperationType.REPLACE, self.any_path, self.any_value)
        patch = jsonpatch.JsonPatch([operation])

        # Act
        jsonmove = ps.JsonMove.from_patch(patch)

        # Assert
        self.verify_jsonmove(operation,
                             OperationType.REPLACE,
                             self.any_tokens,
                             self.any_tokens,
                             jsonmove)

    def test_from_patch__add_op__add_jsonmove(self):
        # Arrange
        operation = self.operation_wrapper.create(OperationType.ADD, self.any_path, self.any_value)
        patch = jsonpatch.JsonPatch([operation])

        # Act
        jsonmove = ps.JsonMove.from_patch(patch)

        # Assert
        self.verify_jsonmove(operation,
                             OperationType.ADD,
                             self.any_tokens,
                             self.any_tokens,
                             jsonmove)

    def test_from_patch__add_op_with_list_indexes__add_jsonmove(self):
        # Arrange
        path = "/table1/key11/list1111/3"
        value = "value11111"
         # From a JsonPatch it is not possible to figure out if the '3' is an item in a list or a dictionary,
         # will assume by default a dictionary for simplicity.
        tokens = ["table1", "key11", "list1111", "3"]
        operation = self.operation_wrapper.create(OperationType.ADD, path, value)
        patch = jsonpatch.JsonPatch([operation])

        # Act
        jsonmove = ps.JsonMove.from_patch(patch)

        # Assert
        self.verify_jsonmove(operation,
                             OperationType.ADD,
                             tokens,
                             tokens,
                             jsonmove)

    def test_from_patch__replace_whole_config__whole_config_jsonmove(self):
        # Arrange
        tokens = []
        path = ""
        value = {"table1": {"key1": "value1"} }
        operation = self.operation_wrapper.create(OperationType.REPLACE, path, value)
        patch = jsonpatch.JsonPatch([operation])

        # Act
        jsonmove = ps.JsonMove.from_patch(patch)

        # Assert
        self.verify_jsonmove(operation,
                             OperationType.REPLACE,
                             tokens,
                             tokens,
                             jsonmove)

    def verify_jsonmove(self,
                        expected_operation,
                        expected_op_type,
                        expected_current_config_tokens,
                        expected_target_config_tokens,
                        jsonmove):
        expected_patch = jsonpatch.JsonPatch([expected_operation])
        self.assertEqual(expected_patch, jsonmove.patch)
        self.assertEqual(expected_op_type, jsonmove.op_type)
        self.assertListEqual(expected_current_config_tokens, jsonmove.current_config_tokens)
        self.assertEqual(expected_target_config_tokens, jsonmove.target_config_tokens)

class TestMoveWrapper(unittest.TestCase):
    def setUp(self):
        self.any_current_config = {}
        self.any_target_config = {}
        self.any_diff = ps.Diff(self.any_current_config, self.any_target_config)
        self.any_move = Mock()
        self.any_other_move1 = Mock()
        self.any_other_move2 = Mock()
        self.any_extended_move = Mock()
        self.any_other_extended_move1 = Mock()
        self.any_other_extended_move2 = Mock()

        self.single_move_generator = Mock()
        self.single_move_generator.generate.side_effect = \
            create_side_effect_dict({(str(self.any_diff),): [self.any_move]})

        self.another_single_move_generator = Mock()
        self.another_single_move_generator.generate.side_effect = \
            create_side_effect_dict({(str(self.any_diff),): [self.any_other_move1]})

        self.multiple_move_generator = Mock()
        self.multiple_move_generator.generate.side_effect = create_side_effect_dict(
            {(str(self.any_diff),): [self.any_move, self.any_other_move1, self.any_other_move2]})

        self.single_move_extender = Mock()
        self.single_move_extender.extend.side_effect = create_side_effect_dict(
            {
                (str(self.any_move), str(self.any_diff)): [self.any_extended_move],
                (str(self.any_extended_move), str(self.any_diff)): [], # As first extended move will be extended
                (str(self.any_other_extended_move1), str(self.any_diff)): [] # Needed when mixed with other extenders
            })

        self.another_single_move_extender = Mock()
        self.another_single_move_extender.extend.side_effect = create_side_effect_dict(
            {
                (str(self.any_move), str(self.any_diff)): [self.any_other_extended_move1],
                (str(self.any_other_extended_move1), str(self.any_diff)): [], # As first extended move will be extended
                (str(self.any_extended_move), str(self.any_diff)): [] # Needed when mixed with other extenders
            })

        self.multiple_move_extender = Mock()
        self.multiple_move_extender.extend.side_effect = create_side_effect_dict(
            {
                (str(self.any_move), str(self.any_diff)): \
                    [self.any_extended_move, self.any_other_extended_move1, self.any_other_extended_move2],
                # All extended moves will be extended
                (str(self.any_extended_move), str(self.any_diff)): [],
                (str(self.any_other_extended_move1), str(self.any_diff)): [],
                (str(self.any_other_extended_move2), str(self.any_diff)): [],
            })

        self.mixed_move_extender = Mock()
        self.mixed_move_extender.extend.side_effect = create_side_effect_dict(
            {
                (str(self.any_move), str(self.any_diff)): [self.any_extended_move],
                (str(self.any_other_move1), str(self.any_diff)): [self.any_other_extended_move1],
                (str(self.any_extended_move), str(self.any_diff)): \
                    [self.any_other_extended_move1, self.any_other_extended_move2],
                # All extended moves will be extended
                (str(self.any_other_extended_move1), str(self.any_diff)): [],
                (str(self.any_other_extended_move2), str(self.any_diff)): [],
            })

        self.fail_move_validator = Mock()
        self.fail_move_validator.validate.side_effect = create_side_effect_dict(
            {(str(self.any_move), str(self.any_diff)): False})

        self.success_move_validator = Mock()
        self.success_move_validator.validate.side_effect = create_side_effect_dict(
            {(str(self.any_move), str(self.any_diff)): True})

    def test_ctor__assigns_values_correctly(self):
        # Arrange
        move_generators = Mock()
        move_extenders = Mock()
        move_validators = Mock()

        # Act
        move_wrapper = ps.MoveWrapper(move_generators, move_extenders, move_validators)

        # Assert
        self.assertIs(move_generators, move_wrapper.move_generators)
        self.assertIs(move_extenders, move_wrapper.move_extenders)
        self.assertIs(move_validators, move_wrapper.move_validators)

    def test_generate__single_move_generator__single_move_returned(self):
        # Arrange
        move_generators = [self.single_move_generator]
        move_wrapper = ps.MoveWrapper(move_generators, [], [])
        expected = [self.any_move]

        # Act
        actual = list(move_wrapper.generate(self.any_diff))

        # Assert
        self.assertListEqual(expected, actual)

    def test_generate__multiple_move_generator__multiple_move_returned(self):
        # Arrange
        move_generators = [self.multiple_move_generator]
        move_wrapper = ps.MoveWrapper(move_generators, [], [])
        expected = [self.any_move, self.any_other_move1, self.any_other_move2]

        # Act
        actual = list(move_wrapper.generate(self.any_diff))

        # Assert
        self.assertListEqual(expected, actual)

    def test_generate__different_move_generators__different_moves_returned(self):
        # Arrange
        move_generators = [self.single_move_generator, self.another_single_move_generator]
        move_wrapper = ps.MoveWrapper(move_generators, [], [])
        expected = [self.any_move, self.any_other_move1]

        # Act
        actual = list(move_wrapper.generate(self.any_diff))

        # Assert
        self.assertListEqual(expected, actual)

    def test_generate__duplicate_generated_moves__unique_moves_returned(self):
        # Arrange
        move_generators = [self.single_move_generator, self.single_move_generator]
        move_wrapper = ps.MoveWrapper(move_generators, [], [])
        expected = [self.any_move]

        # Act
        actual = list(move_wrapper.generate(self.any_diff))

        # Assert
        self.assertListEqual(expected, actual)

    def test_generate__single_move_extender__one_extended_move_returned(self):
        # Arrange
        move_generators = [self.single_move_generator]
        move_extenders = [self.single_move_extender]
        move_wrapper = ps.MoveWrapper(move_generators, move_extenders, [])
        expected = [self.any_move, self.any_extended_move]

        # Act
        actual = list(move_wrapper.generate(self.any_diff))

        # Assert
        self.assertListEqual(expected, actual)

    def test_generate__multiple_move_extender__multiple_extended_move_returned(self):
        # Arrange
        move_generators = [self.single_move_generator]
        move_extenders = [self.multiple_move_extender]
        move_wrapper = ps.MoveWrapper(move_generators, move_extenders, [])
        expected = [self.any_move, self.any_extended_move, self.any_other_extended_move1, self.any_other_extended_move2]

        # Act
        actual = list(move_wrapper.generate(self.any_diff))

        # Assert
        self.assertListEqual(expected, actual)

    def test_generate__different_move_extenders__different_extended_moves_returned(self):
        # Arrange
        move_generators = [self.single_move_generator]
        move_extenders = [self.single_move_extender, self.another_single_move_extender]
        move_wrapper = ps.MoveWrapper(move_generators, move_extenders, [])
        expected = [self.any_move, self.any_extended_move, self.any_other_extended_move1]

        # Act
        actual = list(move_wrapper.generate(self.any_diff))

        # Assert
        self.assertListEqual(expected, actual)

    def test_generate__duplicate_extended_moves__unique_moves_returned(self):
        # Arrange
        move_generators = [self.single_move_generator]
        move_extenders = [self.single_move_extender, self.single_move_extender]
        move_wrapper = ps.MoveWrapper(move_generators, move_extenders, [])
        expected = [self.any_move, self.any_extended_move]

        # Act
        actual = list(move_wrapper.generate(self.any_diff))

        # Assert
        self.assertListEqual(expected, actual)

    def test_generate__mixed_extended_moves__unique_moves_returned(self):
        # Arrange
        move_generators = [self.single_move_generator, self.another_single_move_generator]
        move_extenders = [self.mixed_move_extender]
        move_wrapper = ps.MoveWrapper(move_generators, move_extenders, [])
        expected = [self.any_move,
                    self.any_other_move1,
                    self.any_extended_move,
                    self.any_other_extended_move1,
                    self.any_other_extended_move2]

        # Act
        actual = list(move_wrapper.generate(self.any_diff))

        # Assert
        self.assertListEqual(expected, actual)

    def test_validate__validation_fail__false_returned(self):
        # Arrange
        move_validators = [self.fail_move_validator]
        move_wrapper = ps.MoveWrapper([], [], move_validators)

        # Act and assert
        self.assertFalse(move_wrapper.validate(self.any_move, self.any_diff))

    def test_validate__validation_succeed__true_returned(self):
        # Arrange
        move_validators = [self.success_move_validator]
        move_wrapper = ps.MoveWrapper([], [], move_validators)

        # Act and assert
        self.assertTrue(move_wrapper.validate(self.any_move, self.any_diff))

    def test_validate__multiple_validators_last_fail___false_returned(self):
        # Arrange
        move_validators = [self.success_move_validator, self.success_move_validator, self.fail_move_validator]
        move_wrapper = ps.MoveWrapper([], [], move_validators)

        # Act and assert
        self.assertFalse(move_wrapper.validate(self.any_move, self.any_diff))

    def test_validate__multiple_validators_succeed___true_returned(self):
        # Arrange
        move_validators = [self.success_move_validator, self.success_move_validator, self.success_move_validator]
        move_wrapper = ps.MoveWrapper([], [], move_validators)

        # Act and assert
        self.assertTrue(move_wrapper.validate(self.any_move, self.any_diff))

    def test_simulate__applies_move(self):
        # Arrange
        diff = Mock()
        diff.apply_move.side_effect = create_side_effect_dict({(str(self.any_move), ): self.any_diff})
        move_wrapper = ps.MoveWrapper(None, None, None)

        # Act
        actual = move_wrapper.simulate(self.any_move, diff)

        # Assert
        self.assertIs(self.any_diff, actual)

class TestDeleteWholeConfigMoveValidator(unittest.TestCase):
    def setUp(self):
        self.operation_wrapper = OperationWrapper()
        self.validator = ps.DeleteWholeConfigMoveValidator()
        self.any_diff = Mock()
        self.any_non_whole_config_path = "/table1"
        self.whole_config_path = ""

    def test_validate__non_remove_op_non_whole_config__success(self):
        self.verify(OperationType.REPLACE, self.any_non_whole_config_path, True)
        self.verify(OperationType.ADD, self.any_non_whole_config_path, True)

    def test_validate__remove_op_non_whole_config__success(self):
        self.verify(OperationType.REMOVE, self.any_non_whole_config_path, True)

    def test_validate__non_remove_op_whole_config__success(self):
        self.verify(OperationType.REPLACE, self.whole_config_path, True)
        self.verify(OperationType.ADD, self.whole_config_path, True)

    def test_validate__remove_op_whole_config__failure(self):
        self.verify(OperationType.REMOVE, self.whole_config_path, False)

    def verify(self, operation_type, path, expected):
        # Arrange
        value = None
        if operation_type in [OperationType.ADD, OperationType.REPLACE]:
            value = Mock()

        operation = self.operation_wrapper.create(operation_type, path, value)
        move = ps.JsonMove.from_operation(operation)

        # Act
        actual = self.validator.validate(move, self.any_diff)

        # Assert
        self.assertEqual(expected, actual)

class TestUniqueLanesMoveValidator(unittest.TestCase):
    def setUp(self):
        self.validator = ps.UniqueLanesMoveValidator()

    def test_validate__no_port_table__success(self):
        config = {"ACL_TABLE": {}}
        self.validate_target_config(config)

    def test_validate__empty_port_table__success(self):
        config = {"PORT": {}}
        self.validate_target_config(config)

    def test_validate__single_lane__success(self):
        config = {"PORT": {"Ethernet0": {"lanes": "66", "speed":"10000"}}}
        self.validate_target_config(config)

    def test_validate__different_lanes_single_port___success(self):
        config = {"PORT": {"Ethernet0": {"lanes": "66, 67, 68", "speed":"10000"}}}
        self.validate_target_config(config)

    def test_validate__different_lanes_multi_ports___success(self):
        config = {"PORT": {
            "Ethernet0": {"lanes": "64, 65", "speed":"10000"},
            "Ethernet1": {"lanes": "66, 67, 68", "speed":"10000"},
            }}
        self.validate_target_config(config)

    def test_validate__same_lanes_single_port___success(self):
        config = {"PORT": {"Ethernet0": {"lanes": "65, 65", "speed":"10000"}}}
        self.validate_target_config(config, False)

    def validate_target_config(self, target_config, expected=True):
        # Arrange
        current_config = {}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, [], [])

        # Act
        actual = self.validator.validate(move, diff)

        # Assert
        self.assertEqual(expected, actual)

class TestFullConfigMoveValidator(unittest.TestCase):
    def setUp(self):
        self.any_current_config = Mock()
        self.any_target_config = Mock()
        self.any_simulated_config = Mock()
        self.any_diff = ps.Diff(self.any_current_config, self.any_target_config)
        self.any_move = Mock()
        self.any_move.apply.side_effect = \
            create_side_effect_dict({(str(self.any_current_config),): self.any_simulated_config})

    def test_validate__invalid_config_db_after_applying_move__failure(self):
        # Arrange
        config_wrapper = Mock()
        config_wrapper.validate_config_db_config.side_effect = \
            create_side_effect_dict({(str(self.any_simulated_config),): False})
        validator = ps.FullConfigMoveValidator(config_wrapper)

        # Act and assert
        self.assertFalse(validator.validate(self.any_move, self.any_diff))

    def test_validate__valid_config_db_after_applying_move__success(self):
        # Arrange
        config_wrapper = Mock()
        config_wrapper.validate_config_db_config.side_effect = \
            create_side_effect_dict({(str(self.any_simulated_config),): True})
        validator = ps.FullConfigMoveValidator(config_wrapper)

        # Act and assert
        self.assertTrue(validator.validate(self.any_move, self.any_diff))

class TestCreateOnlyMoveValidator(unittest.TestCase):
    def setUp(self):
        self.validator = ps.CreateOnlyMoveValidator(ps.PathAddressing())
        self.any_diff = ps.Diff({}, {})

    def test_validate__no_create_only_field__success(self):
        current_config = {"PORT": {}}
        target_config = {"PORT": {}, "ACL_TABLE": {}}
        self.verify_diff(current_config, target_config)

    def test_validate__same_create_only_field__success(self):
        current_config = {"PORT": {"Ethernet0":{"lanes":"65"}}}
        target_config = {"PORT": {"Ethernet0":{"lanes":"65"}}, "ACL_TABLE": {}}
        self.verify_diff(current_config, target_config)

    def test_validate__different_create_only_field__failure(self):
        current_config = {"PORT": {"Ethernet0":{"lanes":"65"}}}
        target_config = {"PORT": {"Ethernet0":{"lanes":"66"}}, "ACL_TABLE": {}}
        self.verify_diff(current_config, target_config, expected=False)

    def test_validate__different_create_only_field_directly_updated__failure(self):
        current_config = {"PORT": {"Ethernet0":{"lanes":"65"}}}
        target_config = {"PORT": {"Ethernet0":{"lanes":"66"}}, "ACL_TABLE": {}}
        self.verify_diff(current_config,
                         target_config,
                         ["PORT", "Ethernet0", "lanes"],
                         ["PORT", "Ethernet0", "lanes"],
                         False)

    def test_validate__different_create_only_field_updating_parent__failure(self):
        current_config = {"PORT": {"Ethernet0":{"lanes":"65"}}}
        target_config = {"PORT": {"Ethernet0":{"lanes":"66"}}, "ACL_TABLE": {}}
        self.verify_diff(current_config,
                         target_config,
                         ["PORT", "Ethernet0"],
                         ["PORT", "Ethernet0"],
                         False)

    def test_validate__different_create_only_field_updating_grandparent__failure(self):
        current_config = {"PORT": {"Ethernet0":{"lanes":"65"}}}
        target_config = {"PORT": {"Ethernet0":{"lanes":"66"}}, "ACL_TABLE": {}}
        self.verify_diff(current_config,
                         target_config,
                         ["PORT"],
                         ["PORT"],
                         False)

    def test_validate__same_create_only_field_directly_updated__success(self):
        current_config = {"PORT": {"Ethernet0":{"lanes":"65"}}}
        target_config = {"PORT": {"Ethernet0":{"lanes":"65"}}, "ACL_TABLE": {}}
        self.verify_diff(current_config,
                         target_config,
                         ["PORT", "Ethernet0", "lanes"],
                         ["PORT", "Ethernet0", "lanes"])

    def test_validate__same_create_only_field_updating_parent__success(self):
        current_config = {"PORT": {"Ethernet0":{"lanes":"65"}}}
        target_config = {"PORT": {"Ethernet0":{"lanes":"65"}}, "ACL_TABLE": {}}
        self.verify_diff(current_config,
                         target_config,
                         ["PORT", "Ethernet0"],
                         ["PORT", "Ethernet0"])

    def test_validate__same_create_only_field_updating_grandparent__success(self):
        current_config = {"PORT": {"Ethernet0":{"lanes":"65"}}}
        target_config = {"PORT": {"Ethernet0":{"lanes":"65"}}, "ACL_TABLE": {}}
        self.verify_diff(current_config,
                         target_config,
                         ["PORT"],
                         ["PORT"])

    def test_validate__added_create_only_field_parent_exist__failure(self):
        current_config = {"PORT": {"Ethernet0":{}}}
        target_config = {"PORT": {"Ethernet0":{"lanes":"65"}}, "ACL_TABLE": {}}
        self.verify_diff(current_config,
                         target_config,
                         ["PORT"],
                         ["PORT"],
                         expected=False)

    def test_validate__added_create_only_field_parent_doesnot_exist__success(self):
        current_config = {"PORT": {}}
        target_config = {"PORT": {"Ethernet0":{"lanes":"65"}}, "ACL_TABLE": {}}
        self.verify_diff(current_config,
                         target_config,
                         ["PORT"],
                         ["PORT"])

    def test_validate__removed_create_only_field_parent_remain__failure(self):
        current_config = {"PORT": {"Ethernet0":{"lanes":"65"}}, "ACL_TABLE": {}}
        target_config = {"PORT": {"Ethernet0":{}}}
        self.verify_diff(current_config,
                         target_config,
                         ["PORT"],
                         ["PORT"],
                         expected=False)

    def test_validate__removed_create_only_field_parent_doesnot_remain__success(self):
        current_config = {"PORT": {"Ethernet0":{"lanes":"65"}}, "ACL_TABLE": {}}
        target_config = {"PORT": {}}
        self.verify_diff(current_config,
                         target_config,
                         ["PORT"],
                         ["PORT"])

    def test_hard_coded_create_only_paths(self):
        config = {
            "PORT": {
                "Ethernet0":{"lanes":"65"},
                "Ethernet1":{},
                "Ethernet2":{"lanes":"66,67"}
            },
            "LOOPBACK_INTERFACE": {
                "Loopback0":{"vrf_name":"vrf0"},
                "Loopback1":{},
                "Loopback2":{"vrf_name":"vrf1"},
            }}
        expected = [
            "/PORT/Ethernet0/lanes",
            "/PORT/Ethernet2/lanes",
            "/LOOPBACK_INTERFACE/Loopback0/vrf_name",
            "/LOOPBACK_INTERFACE/Loopback2/vrf_name"
        ]
        actual = self.validator._get_create_only_paths(config)

        self.assertCountEqual(expected, actual)

    def verify_diff(self, current_config, target_config, current_config_tokens=None, target_config_tokens=None, expected=True):
        # Arrange
        current_config_tokens = current_config_tokens if current_config_tokens else []
        target_config_tokens = target_config_tokens if target_config_tokens else []
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, current_config_tokens, target_config_tokens)

        # Act
        actual = self.validator.validate(move, diff)

        # Assert
        self.assertEqual(expected, actual)

class TestNoDependencyMoveValidator(unittest.TestCase):
    def setUp(self):
        config_wrapper = ConfigWrapper()
        path_addressing = ps.PathAddressing(config_wrapper)
        self.validator = ps.NoDependencyMoveValidator(path_addressing, config_wrapper)

    def test_validate__add_full_config_has_dependencies__failure(self):
        # Arrange
        # CROPPED_CONFIG_DB_AS_JSON has dependencies between PORT and ACL_TABLE
        diff = ps.Diff(Files.EMPTY_CONFIG_DB, Files.CROPPED_CONFIG_DB_AS_JSON)
        move = ps.JsonMove(diff, OperationType.ADD, [], [])

        # Act and assert
        self.assertFalse(self.validator.validate(move, diff))

    def test_validate__add_full_config_no_dependencies__success(self):
        # Arrange
        diff = ps.Diff(Files.EMPTY_CONFIG_DB, Files.CONFIG_DB_NO_DEPENDENCIES)
        move = ps.JsonMove(diff, OperationType.ADD, [], [])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def test_validate__add_table_has_no_dependencies__success(self):
        # Arrange
        target_config = Files.CROPPED_CONFIG_DB_AS_JSON
        # prepare current config by removing ACL_TABLE from current config
        current_config = self.prepare_config(target_config, jsonpatch.JsonPatch([
            {"op": "remove", "path":"/ACL_TABLE"}
        ]))
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.ADD, ["ACL_TABLE"], ["ACL_TABLE"])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def test_validate__remove_full_config_has_dependencies__failure(self):
        # Arrange
        # CROPPED_CONFIG_DB_AS_JSON has dependencies between PORT and ACL_TABLE
        diff = ps.Diff(Files.CROPPED_CONFIG_DB_AS_JSON, Files.EMPTY_CONFIG_DB)
        move = ps.JsonMove(diff, OperationType.REMOVE, [], [])

        # Act and assert
        self.assertFalse(self.validator.validate(move, diff))

    def test_validate__remove_full_config_no_dependencies__success(self):
        # Arrange
        diff = ps.Diff(Files.EMPTY_CONFIG_DB, Files.CONFIG_DB_NO_DEPENDENCIES)
        move = ps.JsonMove(diff, OperationType.REMOVE, [], [])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def test_validate__remove_table_has_no_dependencies__success(self):
        # Arrange
        current_config = Files.CROPPED_CONFIG_DB_AS_JSON
        target_config = self.prepare_config(current_config, jsonpatch.JsonPatch([
            {"op": "remove", "path":"/ACL_TABLE"}
        ]))
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REMOVE, ["ACL_TABLE"])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def test_validate__replace_whole_config_item_added_ref_added__failure(self):
        # Arrange
        target_config = Files.SIMPLE_CONFIG_DB_INC_DEPS
        # prepare current config by removing an item and its ref from target config
        current_config = self.prepare_config(target_config, jsonpatch.JsonPatch([
            {"op": "replace", "path":"/ACL_TABLE/EVERFLOW/ports/0", "value":""},
            {"op": "remove", "path":"/PORT/Ethernet0"}
        ]))

        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, [], [])

        # Act and assert
        self.assertFalse(self.validator.validate(move, diff))

    def test_validate__replace_whole_config_item_removed_ref_removed__false(self):
        # Arrange
        current_config = Files.SIMPLE_CONFIG_DB_INC_DEPS
        # prepare target config by removing an item and its ref from current config
        target_config = self.prepare_config(current_config, jsonpatch.JsonPatch([
            {"op": "replace", "path":"/ACL_TABLE/EVERFLOW/ports/0", "value":""},
            {"op": "remove", "path":"/PORT/Ethernet0"}
        ]))

        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, [], [])

        # Act and assert
        self.assertFalse(self.validator.validate(move, diff))

    def test_validate__replace_whole_config_item_same_ref_added__true(self):
        # Arrange
        target_config = Files.SIMPLE_CONFIG_DB_INC_DEPS
        # prepare current config by removing ref from target config
        current_config = self.prepare_config(target_config, jsonpatch.JsonPatch([
            {"op": "replace", "path":"/ACL_TABLE/EVERFLOW/ports/0", "value":""}
        ]))

        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, [], [])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def test_validate__replace_whole_config_item_same_ref_removed__true(self):
        # Arrange
        current_config= Files.SIMPLE_CONFIG_DB_INC_DEPS
        # prepare target config by removing ref from current config
        target_config = self.prepare_config(current_config, jsonpatch.JsonPatch([
            {"op": "replace", "path":"/ACL_TABLE/EVERFLOW/ports/0", "value":""}
        ]))

        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, [], [])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def test_validate__replace_whole_config_item_same_ref_same__true(self):
        # Arrange
        current_config= Files.SIMPLE_CONFIG_DB_INC_DEPS
        # prepare target config by removing ref from current config
        target_config = current_config

        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, [], [])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def test_validate__replace_list_item_different_location_than_target_and_no_deps__true(self):
        # Arrange
        current_config = {
            "VLAN": {
                "Vlan100": {
                    "vlanid": "100",
                    "dhcp_servers": [
                        "192.0.0.1",
                        "192.0.0.2"
                    ]
                }
            }
        }
        target_config = {
            "VLAN": {
                "Vlan100": {
                    "vlanid": "100",
                    "dhcp_servers": [
                        "192.0.0.3"
                    ]
                }
            }
        }
        diff = ps.Diff(current_config, target_config)
        # the target tokens point to location 0 which exist in target_config
        # but the replace operation is operating on location 1 in current_config
        move = ps.JsonMove(diff, OperationType.REPLACE, ["VLAN", "Vlan100", "dhcp_servers", 1], ["VLAN", "Vlan100", "dhcp_servers", 0])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def prepare_config(self, config, patch):
        return patch.apply(config)

class TestNoEmptyTableMoveValidator(unittest.TestCase):
    def setUp(self):
        path_addressing = ps.PathAddressing()
        self.validator = ps.NoEmptyTableMoveValidator(path_addressing)

    def test_validate__no_changes__success(self):
        # Arrange
        current_config = {"some_table":{"key1":"value1", "key2":"value2"}}
        target_config = {"some_table":{"key1":"value1", "key2":"value22"}}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, ["some_table", "key1"], ["some_table", "key1"])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def test_validate__change_but_no_empty_table__success(self):
        # Arrange
        current_config = {"some_table":{"key1":"value1", "key2":"value2"}}
        target_config = {"some_table":{"key1":"value1", "key2":"value22"}}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, ["some_table", "key2"], ["some_table", "key2"])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def test_validate__single_empty_table__failure(self):
        # Arrange
        current_config = {"some_table":{"key1":"value1", "key2":"value2"}}
        target_config = {"some_table":{}}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, ["some_table"], ["some_table"])

        # Act and assert
        self.assertFalse(self.validator.validate(move, diff))

    def test_validate__whole_config_replace_single_empty_table__failure(self):
        # Arrange
        current_config = {"some_table":{"key1":"value1", "key2":"value2"}}
        target_config = {"some_table":{}}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, [], [])

        # Act and assert
        self.assertFalse(self.validator.validate(move, diff))

    def test_validate__whole_config_replace_mix_of_empty_and_non_empty__failure(self):
        # Arrange
        current_config = {"some_table":{"key1":"value1"}, "other_table":{"key2":"value2"}}
        target_config = {"some_table":{"key1":"value1"}, "other_table":{}}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, [], [])

        # Act and assert
        self.assertFalse(self.validator.validate(move, diff))

    def test_validate__whole_config_multiple_empty_tables__failure(self):
        # Arrange
        current_config = {"some_table":{"key1":"value1"}, "other_table":{"key2":"value2"}}
        target_config = {"some_table":{}, "other_table":{}}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REPLACE, [], [])

        # Act and assert
        self.assertFalse(self.validator.validate(move, diff))

    def test_validate__remove_key_empties_a_table__failure(self):
        # Arrange
        current_config = {"some_table":{"key1":"value1"}, "other_table":{"key2":"value2"}}
        target_config = {"some_table":{"key1":"value1"}, "other_table":{}}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REMOVE, ["other_table", "key2"], [])

        # Act and assert
        self.assertFalse(self.validator.validate(move, diff))

    def test_validate__remove_key_but_table_has_other_keys__success(self):
        # Arrange
        current_config = {"some_table":{"key1":"value1"}, "other_table":{"key2":"value2", "key3":"value3"}}
        target_config = {"some_table":{"key1":"value1"}, "other_table":{"key3":"value3"}}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REMOVE, ["other_table", "key2"], [])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def test_validate__remove_whole_table__success(self):
        # Arrange
        current_config = {"some_table":{"key1":"value1"}, "other_table":{"key2":"value2"}}
        target_config = {"some_table":{"key1":"value1"}}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.REMOVE, ["other_table"], [])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

    def test_validate__add_empty_table__failure(self):
        # Arrange
        current_config = {"some_table":{"key1":"value1"}, "other_table":{"key2":"value2"}}
        target_config = {"new_table":{}}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.ADD, ["new_table"], ["new_table"])

        # Act and assert
        self.assertFalse(self.validator.validate(move, diff))

    def test_validate__add_non_empty_table__success(self):
        # Arrange
        current_config = {"some_table":{"key1":"value1"}, "other_table":{"key2":"value2"}}
        target_config = {"new_table":{"key3":"value3"}}
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, OperationType.ADD, ["new_table"], ["new_table"])

        # Act and assert
        self.assertTrue(self.validator.validate(move, diff))

class TestLowLevelMoveGenerator(unittest.TestCase):
    def setUp(self):
        path_addressing = PathAddressing()
        self.generator = ps.LowLevelMoveGenerator(path_addressing)

    def test_generate__no_diff__no_moves(self):
        self.verify()

    def test_generate__replace_key__replace_move(self):
        self.verify(tc_ops=[{"op": "replace", 'path': '/PORT/Ethernet0/description', 'value':'any-desc'}])

    def test_generate__leaf_key_missing__add_move(self):
        self.verify(
            cc_ops=[{"op": "remove", 'path': '/ACL_TABLE/EVERFLOW/policy_desc'}],
            ex_ops=[{"op": "add", 'path': '/ACL_TABLE/EVERFLOW/policy_desc', 'value':'EVERFLOW'}]
            )

    def test_generate__leaf_key_additional__remove_move(self):
        self.verify(
            tc_ops=[{"op": "remove", 'path': '/ACL_TABLE/EVERFLOW/policy_desc'}]
            )

    def test_generate__table_missing__add_leafs_moves(self):
        self.verify(
            cc_ops=[{"op": "remove", 'path': '/VLAN'}],
            ex_ops=[{'op': 'add', 'path': '/VLAN', 'value': {'Vlan1000': {'vlanid': '1000'}}},
                    {'op': 'add', 'path': '/VLAN', 'value': {'Vlan1000': {'dhcp_servers': ['192.0.0.1']}}},
                    {'op': 'add', 'path': '/VLAN', 'value': {'Vlan1000': {'dhcp_servers': ['192.0.0.2']}}},
                    {'op': 'add', 'path': '/VLAN', 'value': {'Vlan1000': {'dhcp_servers': ['192.0.0.3']}}},
                    {'op': 'add', 'path': '/VLAN', 'value': {'Vlan1000': {'dhcp_servers': ['192.0.0.4']}}}]
            )

    def test_generate__table_additional__remove_leafs_moves(self):
        self.verify(
            tc_ops=[{"op": "remove", 'path': '/VLAN'}],
            ex_ops=[{'op': 'remove', 'path': '/VLAN/Vlan1000/vlanid'},
                    {'op': 'remove', 'path': '/VLAN/Vlan1000/dhcp_servers/0'},
                    {'op': 'remove', 'path': '/VLAN/Vlan1000/dhcp_servers/1'},
                    {'op': 'remove', 'path': '/VLAN/Vlan1000/dhcp_servers/2'},
                    {'op': 'remove', 'path': '/VLAN/Vlan1000/dhcp_servers/3'}]
            )

    def test_generate__leaf_table_missing__add_table(self):
        self.verify(
            tc_ops=[{"op": "add", 'path': '/NEW_TABLE', 'value':{}}]
            )

    def test_generate__leaf_table_additional__remove_table(self):
        self.verify(
            cc_ops=[{"op": "add", 'path': '/NEW_TABLE', 'value':{}}],
            ex_ops=[{"op": "remove", 'path': '/NEW_TABLE'}]
            )

    def test_generate__replace_list_item__remove_add_replace_moves(self):
        self.verify(
            tc_ops=[{"op": "replace", 'path': '/ACL_TABLE/EVERFLOW/ports/0', 'value':'Ethernet0'}],
            ex_ops=[
                {"op": "remove", 'path': '/ACL_TABLE/EVERFLOW/ports/0'},
                {"op": "add", 'path': '/ACL_TABLE/EVERFLOW/ports/0', 'value':'Ethernet0'},
                {"op": "replace", 'path': '/ACL_TABLE/EVERFLOW/ports/0', 'value':'Ethernet0'},
            ])

    def test_generate__remove_list_item__remove_move(self):
        self.verify(
            tc_ops=[{"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers/0'}])

    def test_generate__remove_multiple_list_items__multiple_remove_moves(self):
        self.verify(
            tc_ops=[{"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers/0'},
                    {"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers/0'}],
            ex_ops=[{"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers/0'},
                    {"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers/1'}]
            )

    def test_generate__remove_all_list_items__multiple_remove_moves(self):
        self.verify(
            tc_ops=[{"op": "replace", 'path': '/VLAN/Vlan1000/dhcp_servers', 'value':[]}],
            ex_ops=[{"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers/0'},
                    {"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers/2'},
                    {"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers/3'},
                    {"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers/1'}]
            )

    def test_generate__add_list_items__add_move(self):
        self.verify(
            tc_ops=[{"op": "add", 'path': '/VLAN/Vlan1000/dhcp_servers/0', 'value':'192.168.1.5'}]
            )

    def test_generate__add_multiple_list_items__multiple_add_moves(self):
        self.verify(
            tc_ops=[{"op": "add", 'path': '/VLAN/Vlan1000/dhcp_servers/0', 'value':'192.168.1.5'},
                    {"op": "add", 'path': '/VLAN/Vlan1000/dhcp_servers/3', 'value':'192.168.1.6'}]
            )

    def test_generate__add_all_list_items__multiple_add_moves(self):
        self.verify(
            cc_ops=[{"op": "replace", 'path': '/VLAN/Vlan1000/dhcp_servers', 'value':[]}],
            ex_ops=[{"op": "add", 'path': '/VLAN/Vlan1000/dhcp_servers/0', 'value':'192.0.0.1'},
                    {"op": "add", 'path': '/VLAN/Vlan1000/dhcp_servers/0', 'value':'192.0.0.2'},
                    {"op": "add", 'path': '/VLAN/Vlan1000/dhcp_servers/0', 'value':'192.0.0.3'},
                    {"op": "add", 'path': '/VLAN/Vlan1000/dhcp_servers/0', 'value':'192.0.0.4'}]
            )

    def test_generate__replace_multiple_list_items__multiple_remove_add_replace_moves(self):
        self.verify(
            tc_ops=[{"op": "replace", 'path': '/VLAN/Vlan1000/dhcp_servers/0', 'value':'192.168.1.5'},
                    {"op": "replace", 'path': '/VLAN/Vlan1000/dhcp_servers/3', 'value':'192.168.1.6'}],
            ex_ops=[{"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers/0'},
                    {"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers/3'},
                    {"op": "add", 'path': '/VLAN/Vlan1000/dhcp_servers/0', 'value':'192.168.1.5'},
                    {"op": "add", 'path': '/VLAN/Vlan1000/dhcp_servers/3', 'value':'192.168.1.6'},
                    {"op": "replace", 'path': '/VLAN/Vlan1000/dhcp_servers/0', 'value':'192.168.1.5'},
                    {"op": "replace", 'path': '/VLAN/Vlan1000/dhcp_servers/3', 'value':'192.168.1.6'},
                    {"op": "replace", 'path': '/VLAN/Vlan1000/dhcp_servers/3', 'value':'192.168.1.5'},
                    {"op": "replace", 'path': '/VLAN/Vlan1000/dhcp_servers/0', 'value':'192.168.1.6'}]
            )

    def test_generate__different_order_list_items__whole_list_replace_move(self):
        self.verify(
            tc_ops=[{"op": "replace", 'path': '/VLAN/Vlan1000/dhcp_servers', 'value':[
                "192.0.0.4",
                "192.0.0.3",
                "192.0.0.2",
                "192.0.0.1"
            ]}])

    def test_generate__whole_list_missing__add_items_moves(self):
        self.verify(
            cc_ops=[{"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers'}],
            ex_ops=[{'op': 'add', 'path': '/VLAN/Vlan1000/dhcp_servers', 'value': ['192.0.0.1']},
                    {'op': 'add', 'path': '/VLAN/Vlan1000/dhcp_servers', 'value': ['192.0.0.2']},
                    {'op': 'add', 'path': '/VLAN/Vlan1000/dhcp_servers', 'value': ['192.0.0.3']},
                    {'op': 'add', 'path': '/VLAN/Vlan1000/dhcp_servers', 'value': ['192.0.0.4']}])

    def test_generate__whole_list_additional__remove_items_moves(self):
        self.verify(
            tc_ops=[{"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers'}],
            ex_ops=[{'op': 'remove', 'path': '/VLAN/Vlan1000/dhcp_servers/0'},
                    {'op': 'remove', 'path': '/VLAN/Vlan1000/dhcp_servers/1'},
                    {'op': 'remove', 'path': '/VLAN/Vlan1000/dhcp_servers/2'},
                    {'op': 'remove', 'path': '/VLAN/Vlan1000/dhcp_servers/3'}])

    def test_generate__empty_list_missing__add_whole_list(self):
        self.verify(
            tc_ops=[{"op": "replace", 'path': '/VLAN/Vlan1000/dhcp_servers', 'value':[]}],
            cc_ops=[{"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers'}],
            ex_ops=[{'op': 'add', 'path': '/VLAN/Vlan1000/dhcp_servers', 'value':[]}])

    def test_generate__empty_list_additional__remove_whole_list(self):
        self.verify(
            tc_ops=[{"op": "remove", 'path': '/VLAN/Vlan1000/dhcp_servers'}],
            cc_ops=[{"op": "replace", 'path': '/VLAN/Vlan1000/dhcp_servers', 'value':[]}],
            ex_ops=[{'op': 'remove', 'path': '/VLAN/Vlan1000/dhcp_servers'}])

    def test_generate__dpb_1_to_4_example(self):
        # Arrange
        diff = ps.Diff(Files.DPB_1_SPLIT_FULL_CONFIG, Files.DPB_4_SPLITS_FULL_CONFIG)

        # Act
        moves = list(self.generator.generate(diff))

        # Assert
        self.verify_moves([{'op': 'replace', 'path': '/PORT/Ethernet0/alias', 'value': 'Eth1/1'},
                           {'op': 'replace', 'path': '/PORT/Ethernet0/lanes', 'value': '65'},
                           {'op': 'replace', 'path': '/PORT/Ethernet0/description', 'value': ''},
                           {'op': 'replace', 'path': '/PORT/Ethernet0/speed', 'value': '10000'},
                           {'op': 'add', 'path': '/PORT/Ethernet1', 'value': {'alias': 'Eth1/2'}},
                           {'op': 'add', 'path': '/PORT/Ethernet1', 'value': {'lanes': '66'}},
                           {'op': 'add', 'path': '/PORT/Ethernet1', 'value': {'description': ''}},
                           {'op': 'add', 'path': '/PORT/Ethernet1', 'value': {'speed': '10000'}},
                           {'op': 'add', 'path': '/PORT/Ethernet2', 'value': {'alias': 'Eth1/3'}},
                           {'op': 'add', 'path': '/PORT/Ethernet2', 'value': {'lanes': '67'}},
                           {'op': 'add', 'path': '/PORT/Ethernet2', 'value': {'description': ''}},
                           {'op': 'add', 'path': '/PORT/Ethernet2', 'value': {'speed': '10000'}},
                           {'op': 'add', 'path': '/PORT/Ethernet3', 'value': {'alias': 'Eth1/4'}},
                           {'op': 'add', 'path': '/PORT/Ethernet3', 'value': {'lanes': '68'}},
                           {'op': 'add', 'path': '/PORT/Ethernet3', 'value': {'description': ''}},
                           {'op': 'add', 'path': '/PORT/Ethernet3', 'value': {'speed': '10000'}},
                           {'op': 'add', 'path': '/ACL_TABLE/NO-NSW-PACL-V4/ports/1', 'value': 'Ethernet1'},
                           {'op': 'add', 'path': '/ACL_TABLE/NO-NSW-PACL-V4/ports/1', 'value': 'Ethernet2'},
                           {'op': 'add', 'path': '/ACL_TABLE/NO-NSW-PACL-V4/ports/1', 'value': 'Ethernet3'},
                           {'op': 'add', 'path': '/VLAN_MEMBER/Vlan100|Ethernet1', 'value': {'tagging_mode': 'untagged'}},
                           {'op': 'add', 'path': '/VLAN_MEMBER/Vlan100|Ethernet2', 'value': {'tagging_mode': 'untagged'}},
                           {'op': 'add', 'path': '/VLAN_MEMBER/Vlan100|Ethernet3', 'value': {'tagging_mode': 'untagged'}}],
                          moves)

    def test_generate__dpb_4_to_1_example(self):
        # Arrange
        diff = ps.Diff(Files.DPB_4_SPLITs_FULL_CONFIG, Files.DPB_1_SPLIT_FULL_CONFIG)

        # Act
        moves = list(self.generator.generate(diff))

        # Assert
        self.verify_moves([{'op': 'replace', 'path': '/PORT/Ethernet0/alias', 'value': 'Eth1'},
                           {'op': 'replace', 'path': '/PORT/Ethernet0/lanes', 'value': '65, 66, 67, 68'},
                           {'op': 'replace', 'path': '/PORT/Ethernet0/description', 'value': 'Ethernet0 100G link'},
                           {'op': 'replace', 'path': '/PORT/Ethernet0/speed', 'value': '100000'},
                           {'op': 'remove', 'path': '/PORT/Ethernet1/alias'},
                           {'op': 'remove', 'path': '/PORT/Ethernet1/lanes'},
                           {'op': 'remove', 'path': '/PORT/Ethernet1/description'},
                           {'op': 'remove', 'path': '/PORT/Ethernet1/speed'},
                           {'op': 'remove', 'path': '/PORT/Ethernet2/alias'},
                           {'op': 'remove', 'path': '/PORT/Ethernet2/lanes'},
                           {'op': 'remove', 'path': '/PORT/Ethernet2/description'},
                           {'op': 'remove', 'path': '/PORT/Ethernet2/speed'},
                           {'op': 'remove', 'path': '/PORT/Ethernet3/alias'},
                           {'op': 'remove', 'path': '/PORT/Ethernet3/lanes'},
                           {'op': 'remove', 'path': '/PORT/Ethernet3/description'},
                           {'op': 'remove', 'path': '/PORT/Ethernet3/speed'},
                           {'op': 'remove', 'path': '/ACL_TABLE/NO-NSW-PACL-V4/ports/1'},
                           {'op': 'remove', 'path': '/ACL_TABLE/NO-NSW-PACL-V4/ports/2'},
                           {'op': 'remove', 'path': '/ACL_TABLE/NO-NSW-PACL-V4/ports/3'},
                           {'op': 'remove', 'path': '/VLAN_MEMBER/Vlan100|Ethernet1/tagging_mode'},
                           {'op': 'remove', 'path': '/VLAN_MEMBER/Vlan100|Ethernet2/tagging_mode'},
                           {'op': 'remove', 'path': '/VLAN_MEMBER/Vlan100|Ethernet3/tagging_mode'}],
                          moves)

    def verify(self, tc_ops=None, cc_ops=None, ex_ops=None):
        """
        Generate a diff where target config is modified using the given tc_ops.
        The expected low level moves should ex_ops if it is not None, otherwise tc_ops
        """
        # Arrange
        diff = self.get_diff(target_config_ops=tc_ops, current_config_ops=cc_ops)
        expected = ex_ops if ex_ops is not None else \
                   tc_ops if tc_ops is not None else \
                   []

        # Act
        actual = self.generator.generate(diff)

        # Assert
        self.verify_moves(expected, actual)

    def verify_moves(self, ops, moves):
        moves_ops = [list(move.patch)[0] for move in moves]
        self.assertCountEqual(ops, moves_ops)

    def get_diff(self, target_config_ops = None, current_config_ops = None):
        current_config = Files.CROPPED_CONFIG_DB_AS_JSON
        if current_config_ops:
            cc_patch = jsonpatch.JsonPatch(current_config_ops)
            current_config = cc_patch.apply(current_config)

        target_config = Files.CROPPED_CONFIG_DB_AS_JSON
        if target_config_ops:
            tc_patch = jsonpatch.JsonPatch(target_config_ops)
            target_config = tc_patch.apply(target_config)

        return ps.Diff(current_config, target_config)

class TestUpperLevelMoveExtender(unittest.TestCase):
    def setUp(self):
        self.extender = ps.UpperLevelMoveExtender()
        self.any_diff = ps.Diff(Files.ANY_CONFIG_DB, Files.ANY_CONFIG_DB)

    def test_extend__root_level_move__no_extended_moves(self):
        self.verify(OperationType.REMOVE, [])
        self.verify(OperationType.ADD, [], [])
        self.verify(OperationType.REPLACE, [], [])

    def test_extend__remove_key_upper_level_does_not_exist__remove_upper_level(self):
        self.verify(OperationType.REMOVE,
                    ["ACL_TABLE", "EVERFLOW", "policy_desc"],
                    tc_ops=[{'op':'remove', 'path':'/ACL_TABLE/EVERFLOW'}],
                    ex_ops=[{'op':'remove', 'path':'/ACL_TABLE/EVERFLOW'}])

    def test_extend__remove_key_upper_level_does_exist__replace_upper_level(self):
        self.verify(OperationType.REMOVE,
                    ["ACL_TABLE", "EVERFLOW", "policy_desc"],
                    tc_ops=[{'op':'remove', 'path':'/ACL_TABLE/EVERFLOW/policy_desc'}],
                    ex_ops=[{'op':'replace', 'path':'/ACL_TABLE/EVERFLOW', 'value':{
                        "ports": [
                            "Ethernet8"
                        ],
                        "stage": "ingress",
                        "type": "MIRROR"
                    }}])

    def test_extend__remove_list_item_upper_level_does_not_exist__remove_upper_level(self):
        self.verify(OperationType.REMOVE,
                    ["VLAN", "Vlan1000", "dhcp_servers", 1],
                    tc_ops=[{'op':'remove', 'path':'/VLAN/Vlan1000/dhcp_servers'}],
                    ex_ops=[{'op':'remove', 'path':'/VLAN/Vlan1000/dhcp_servers'}])

    def test_extend__remove_list_item_upper_level_does_exist__replace_upper_level(self):
        self.verify(OperationType.REMOVE,
                    ["VLAN", "Vlan1000", "dhcp_servers", 1],
                    tc_ops=[{'op':'remove', 'path':'/VLAN/Vlan1000/dhcp_servers/1'}],
                    ex_ops=[{'op':'replace', 'path':'/VLAN/Vlan1000/dhcp_servers', 'value':[
                        "192.0.0.1",
                        "192.0.0.3",
                        "192.0.0.4"
                    ]}])

    def test_extend__add_key_upper_level_missing__add_upper_level(self):
        self.verify(OperationType.ADD,
                    ["ACL_TABLE", "EVERFLOW", "policy_desc"],
                    ["ACL_TABLE", "EVERFLOW", "policy_desc"],
                    cc_ops=[{'op':'remove', 'path':'/ACL_TABLE/EVERFLOW'}],
                    ex_ops=[{'op':'add', 'path':'/ACL_TABLE/EVERFLOW', 'value':{
                        "policy_desc": "EVERFLOW",
                        "ports": [
                            "Ethernet8"
                        ],
                        "stage": "ingress",
                        "type": "MIRROR"
                    }}])

    def test_extend__add_key_upper_level_exist__replace_upper_level(self):
        self.verify(OperationType.ADD,
                    ["ACL_TABLE", "EVERFLOW", "policy_desc"],
                    ["ACL_TABLE", "EVERFLOW", "policy_desc"],
                    cc_ops=[{'op':'remove', 'path':'/ACL_TABLE/EVERFLOW/policy_desc'}],
                    ex_ops=[{'op':'replace', 'path':'/ACL_TABLE/EVERFLOW', 'value':{
                        "policy_desc": "EVERFLOW",
                        "ports": [
                            "Ethernet8"
                        ],
                        "stage": "ingress",
                        "type": "MIRROR"
                    }}])

    def test_extend__add_list_item_upper_level_missing__add_upper_level(self):
        self.verify(OperationType.ADD,
                    ["VLAN", "Vlan1000", "dhcp_servers", 1],
                    ["VLAN", "Vlan1000", "dhcp_servers", 1],
                    cc_ops=[{'op':'remove', 'path':'/VLAN/Vlan1000/dhcp_servers'}],
                    ex_ops=[{'op':'add', 'path':'/VLAN/Vlan1000/dhcp_servers', 'value':[
                        "192.0.0.1",
                        "192.0.0.2",
                        "192.0.0.3",
                        "192.0.0.4"
                    ]}])

    def test_extend__add_list_item_upper_level_exist__replace_upper_level(self):
        self.verify(OperationType.ADD,
                    ["VLAN", "Vlan1000", "dhcp_servers", 1],
                    ["VLAN", "Vlan1000", "dhcp_servers", 1],
                    cc_ops=[{'op':'remove', 'path':'/VLAN/Vlan1000/dhcp_servers/1'}],
                    ex_ops=[{'op':'replace', 'path':'/VLAN/Vlan1000/dhcp_servers', 'value':[
                        "192.0.0.1",
                        "192.0.0.2",
                        "192.0.0.3",
                        "192.0.0.4"
                    ]}])

    def test_extend__add_table__replace_whole_config(self):
        self.verify(OperationType.ADD,
                    ["ACL_TABLE"],
                    ["ACL_TABLE"],
                    cc_ops=[{'op':'remove', 'path':'/ACL_TABLE'}],
                    ex_ops=[{'op':'replace', 'path':'', 'value':Files.CROPPED_CONFIG_DB_AS_JSON}])

    def test_extend__replace_key__replace_upper_level(self):
        self.verify(OperationType.REPLACE,
                    ["ACL_TABLE", "EVERFLOW", "policy_desc"],
                    ["ACL_TABLE", "EVERFLOW", "policy_desc"],
                    cc_ops=[{'op':'replace', 'path':'/ACL_TABLE/EVERFLOW/policy_desc', 'value':'old_desc'}],
                    ex_ops=[{'op':'replace', 'path':'/ACL_TABLE/EVERFLOW', 'value':{
                        "policy_desc": "EVERFLOW",
                        "ports": [
                            "Ethernet8"
                        ],
                        "stage": "ingress",
                        "type": "MIRROR"
                    }}])

    def test_extend__replace_list_item__replace_upper_level(self):
        self.verify(OperationType.REPLACE,
                    ["VLAN", "Vlan1000", "dhcp_servers", 1],
                    ["VLAN", "Vlan1000", "dhcp_servers", 1],
                    cc_ops=[{'op':'replace', 'path':'/VLAN/Vlan1000/dhcp_servers/1', 'value':'192.0.0.7'}],
                    ex_ops=[{'op':'replace', 'path':'/VLAN/Vlan1000/dhcp_servers', 'value':[
                        "192.0.0.1",
                        "192.0.0.2",
                        "192.0.0.3",
                        "192.0.0.4"
                    ]}])

    def test_extend__replace_table__replace_whole_config(self):
        self.verify(OperationType.REPLACE,
                    ["VLAN"],
                    ["VLAN"],
                    cc_ops=[{'op':'replace', 'path':'/VLAN/Vlan1000/dhcp_servers/1', 'value':'192.0.0.7'}],
                    ex_ops=[{'op':'replace', 'path':'', 'value':Files.CROPPED_CONFIG_DB_AS_JSON}])

    def verify(self, op_type, ctokens, ttokens=None, cc_ops=[], tc_ops=[], ex_ops=[]):
        """
        cc_ops, tc_ops are used to build the diff object.
        diff, op_type, ctokens, ttokens  are used to build the move.
        move is extended and the result should match ex_ops.
        """
        # Arrange
        current_config=jsonpatch.JsonPatch(cc_ops).apply(Files.CROPPED_CONFIG_DB_AS_JSON)
        target_config=jsonpatch.JsonPatch(tc_ops).apply(Files.CROPPED_CONFIG_DB_AS_JSON)
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, op_type, ctokens, ttokens)

        # Act
        moves = self.extender.extend(move, diff)

        # Assert
        self.verify_moves(ex_ops, moves)

    def verify_moves(self, ex_ops, moves):
        moves_ops = [list(move.patch)[0] for move in moves]
        self.assertCountEqual(ex_ops, moves_ops)

class TestDeleteInsteadOfReplaceMoveExtender(unittest.TestCase):
    def setUp(self):
        self.extender = ps.DeleteInsteadOfReplaceMoveExtender()

    def test_extend__non_replace__no_extended_moves(self):
        self.verify(OperationType.REMOVE,
                    ["ACL_TABLE"],
                    tc_ops=[{'op':'remove', 'path':'/ACL_TABLE'}],
                    ex_ops=[])
        self.verify(OperationType.ADD,
                    ["ACL_TABLE"],
                    ["ACL_TABLE"],
                    cc_ops=[{'op':'remove', 'path':'/ACL_TABLE'}],
                    ex_ops=[])

    def test_extend__replace_key__delete_key(self):
        self.verify(OperationType.REPLACE,
                    ["ACL_TABLE", "EVERFLOW", "policy_desc"],
                    ["ACL_TABLE", "EVERFLOW", "policy_desc"],
                    cc_ops=[{'op':'replace', 'path':'/ACL_TABLE/EVERFLOW/policy_desc', 'value':'old_desc'}],
                    ex_ops=[{'op':'remove', 'path':'/ACL_TABLE/EVERFLOW/policy_desc'}])

    def test_extend__replace_list_item__delete_list_item(self):
        self.verify(OperationType.REPLACE,
                    ["VLAN", "Vlan1000", "dhcp_servers", 1],
                    ["VLAN", "Vlan1000", "dhcp_servers", 1],
                    cc_ops=[{'op':'replace', 'path':'/VLAN/Vlan1000/dhcp_servers/1', 'value':'192.0.0.7'}],
                    ex_ops=[{'op':'remove', 'path':'/VLAN/Vlan1000/dhcp_servers/1'}])

    def test_extend__replace_table__delete_table(self):
        self.verify(OperationType.REPLACE,
                    ["ACL_TABLE"],
                    ["ACL_TABLE"],
                    cc_ops=[{'op':'replace', 'path':'/ACL_TABLE/EVERFLOW/policy_desc', 'value':'old_desc'}],
                    ex_ops=[{'op':'remove', 'path':'/ACL_TABLE'}])

    def test_extend__replace_whole_config__delete_whole_config(self):
        self.verify(OperationType.REPLACE,
                    [],
                    [],
                    cc_ops=[{'op':'replace', 'path':'/ACL_TABLE/EVERFLOW/policy_desc', 'value':'old_desc'}],
                    ex_ops=[{'op':'remove', 'path':''}])

    def verify(self, op_type, ctokens, ttokens=None, cc_ops=[], tc_ops=[], ex_ops=[]):
        """
        cc_ops, tc_ops are used to build the diff object.
        diff, op_type, ctokens, ttokens  are used to build the move.
        move is extended and the result should match ex_ops.
        """
        # Arrange
        current_config=jsonpatch.JsonPatch(cc_ops).apply(Files.CROPPED_CONFIG_DB_AS_JSON)
        target_config=jsonpatch.JsonPatch(tc_ops).apply(Files.CROPPED_CONFIG_DB_AS_JSON)
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, op_type, ctokens, ttokens)

        # Act
        moves = self.extender.extend(move, diff)

        # Assert
        self.verify_moves(ex_ops, moves)

    def verify_moves(self, ex_ops, moves):
        moves_ops = [list(move.patch)[0] for move in moves]
        self.assertCountEqual(ex_ops, moves_ops)

class DeleteRefsMoveExtender(unittest.TestCase):
    def setUp(self):
        self.extender = ps.DeleteRefsMoveExtender(PathAddressing(ConfigWrapper()))

    def test_extend__non_delete_ops__no_extended_moves(self):
        self.verify(OperationType.ADD,
                    ["ACL_TABLE"],
                    ["ACL_TABLE"],
                    cc_ops=[{'op':'remove', 'path':'/ACL_TABLE'}],
                    ex_ops=[])
        self.verify(OperationType.REPLACE,
                    ["ACL_TABLE"],
                    ["ACL_TABLE"],
                    cc_ops=[{'op':'remove', 'path':'/ACL_TABLE/EVERFLOW'}],
                    ex_ops=[])

    def test_extend__path_with_no_refs__no_extended_moves(self):
        self.verify(OperationType.REMOVE,
                    ["ACL_TABLE"],
                    tc_ops=[{'op':'remove', 'path':'/ACL_TABLE'}],
                    ex_ops=[])

    def test_extend__path_with_direct_refs__extended_moves(self):
        self.verify(OperationType.REMOVE,
                    ["PORT", "Ethernet0"],
                    tc_ops=[{'op':'remove', 'path':'/PORT/Ethernet0'}],
                    ex_ops=[{'op': 'remove', 'path': '/VLAN_MEMBER/Vlan1000|Ethernet0'},
                            {'op': 'remove', 'path': '/ACL_TABLE/NO-NSW-PACL-V4/ports/0'}])

    def test_extend__path_with_refs_to_children__extended_moves(self):
        self.verify(OperationType.REMOVE,
                    ["PORT"],
                    tc_ops=[{'op':'remove', 'path':'/PORT/Ethernet0'}],
                    ex_ops=[{'op': 'remove', 'path': '/VLAN_MEMBER/Vlan1000|Ethernet0'},
                            {'op': 'remove', 'path': '/ACL_TABLE/NO-NSW-PACL-V4/ports/0'},
                            {'op': 'remove', 'path': '/VLAN_MEMBER/Vlan1000|Ethernet4'},
                            {'op': 'remove', 'path': '/ACL_TABLE/DATAACL/ports/0'},
                            {'op': 'remove', 'path': '/VLAN_MEMBER/Vlan1000|Ethernet8'},
                            {'op': 'remove', 'path': '/ACL_TABLE/EVERFLOWV6/ports/0'},
                            {'op': 'remove', 'path': '/ACL_TABLE/EVERFLOW/ports/0'},
                            {'op': 'remove', 'path': '/ACL_TABLE/EVERFLOWV6/ports/1'}])

    def verify(self, op_type, ctokens, ttokens=None, cc_ops=[], tc_ops=[], ex_ops=[]):
        """
        cc_ops, tc_ops are used to build the diff object.
        diff, op_type, ctokens, ttokens  are used to build the move.
        move is extended and the result should match ex_ops.
        """
        # Arrange
        current_config=jsonpatch.JsonPatch(cc_ops).apply(Files.CROPPED_CONFIG_DB_AS_JSON)
        target_config=jsonpatch.JsonPatch(tc_ops).apply(Files.CROPPED_CONFIG_DB_AS_JSON)
        diff = ps.Diff(current_config, target_config)
        move = ps.JsonMove(diff, op_type, ctokens, ttokens)

        # Act
        moves = self.extender.extend(move, diff)

        # Assert
        self.verify_moves(ex_ops, moves)

    def verify_moves(self, ex_ops, moves):
        moves_ops = [list(move.patch)[0] for move in moves]
        self.assertCountEqual(ex_ops, moves_ops)

class TestSortAlgorithmFactory(unittest.TestCase):
    def test_dfs_sorter(self):
        self.verify(ps.Algorithm.DFS, ps.DfsSorter)

    def test_bfs_sorter(self):
        self.verify(ps.Algorithm.BFS, ps.BfsSorter)

    def test_memoization_sorter(self):
        self.verify(ps.Algorithm.MEMOIZATION, ps.MemoizationSorter)

    def verify(self, algo, algo_class):
        # Arrange
        config_wrapper = ConfigWrapper()
        factory = ps.SortAlgorithmFactory(OperationWrapper(), config_wrapper, PathAddressing(config_wrapper))
        expected_generators = [ps.LowLevelMoveGenerator]
        expected_extenders = [ps.UpperLevelMoveExtender, ps.DeleteInsteadOfReplaceMoveExtender, ps.DeleteRefsMoveExtender]
        expected_validator = [ps.DeleteWholeConfigMoveValidator,
                              ps.FullConfigMoveValidator,
                              ps.NoDependencyMoveValidator,
                              ps.UniqueLanesMoveValidator,
                              ps.CreateOnlyMoveValidator,
                              ps.NoEmptyTableMoveValidator]

        # Act
        sorter = factory.create(algo)
        actual_generators = [type(item) for item in sorter.move_wrapper.move_generators]
        actual_extenders = [type(item) for item in sorter.move_wrapper.move_extenders]
        actual_validators = [type(item) for item in sorter.move_wrapper.move_validators]

        # Assert
        self.assertIsInstance(sorter, algo_class)
        self.assertCountEqual(expected_generators, actual_generators)
        self.assertCountEqual(expected_extenders, actual_extenders)
        self.assertCountEqual(expected_validator, actual_validators)

class TestPatchSorter(unittest.TestCase):
    def setUp(self):
        self.config_wrapper = ConfigWrapper()

    def test_patch_sorter_success(self):
        # Format of the JSON file containing the test-cases:
        #
        # {
        #     "<unique_name_for_the_test>":{
        #         "desc":"<brief explanation of the test case>",
        #         "current_config":<the running config to be modified>,
        #         "patch":<the JsonPatch to apply>,
        #         "expected_changes":[<list of expected changes after sorting>]
        #     },
        #     .
        #     .
        #     .
        # }
        data = Files.PATCH_SORTER_TEST_SUCCESS
        skip_exact_change_list_match = False
        for test_case_name in data:
            with self.subTest(name=test_case_name):
                self.run_single_success_case(data[test_case_name], skip_exact_change_list_match)

    def run_single_success_case(self, data, skip_exact_change_list_match):
        current_config = data["current_config"]
        patch = jsonpatch.JsonPatch(data["patch"])
        expected_changes = []
        for item in data["expected_changes"]:
            expected_changes.append(JsonChange(jsonpatch.JsonPatch(item)))

        sorter = self.create_patch_sorter(current_config)

        actual_changes = sorter.sort(patch)

        if not skip_exact_change_list_match:
            self.assertEqual(expected_changes, actual_changes)

        target_config = patch.apply(current_config)
        simulated_config = current_config
        for change in actual_changes:
            simulated_config = change.apply(simulated_config)
            self.assertTrue(self.config_wrapper.validate_config_db_config(simulated_config))
        self.assertEqual(target_config, simulated_config)

    def test_patch_sorter_failure(self):
        # Format of the JSON file containing the test-cases:
        #
        # {
        #     "<unique_name_for_the_test>":{
        #         "desc":"<brief explanation of the test case>",
        #         "current_config":<the running config to be modified>,
        #         "patch":<the JsonPatch to apply>,
        #         "expected_error_substrings":[<list of expected error substrings>]
        #     },
        #     .
        #     .
        #     .
        # }
        data = Files.PATCH_SORTER_TEST_FAILURE
        for test_case_name in data:
            with self.subTest(name=test_case_name):
                self.run_single_failure_case(data[test_case_name])

    def run_single_failure_case(self, data):
        current_config = data["current_config"]
        patch = jsonpatch.JsonPatch(data["patch"])
        expected_error_substrings = data["expected_error_substrings"]

        try:
            sorter = self.create_patch_sorter(current_config)
            sorter.sort(patch)
            self.fail("An exception was supposed to be thrown")
        except Exception as ex:
            notfound_substrings = []
            error = str(ex)
            for substring in expected_error_substrings:
                if substring not in error:
                    notfound_substrings.append(substring)

            if notfound_substrings:
                self.fail(f"Did not find the substrings {notfound_substrings} in the error: '{error}'")

    def test_sort__does_not_remove_tables_without_yang_unintentionally_if_generated_change_replaces_whole_config(self):
        # Arrange
        current_config = Files.CONFIG_DB_AS_JSON # has a table without yang named 'TABLE_WITHOUT_YANG'
        any_patch = Files.SINGLE_OPERATION_CONFIG_DB_PATCH
        target_config = any_patch.apply(current_config)
        sort_algorithm = Mock()
        sort_algorithm.sort = lambda diff: [ps.JsonMove(diff, OperationType.REPLACE, [], [])]
        patch_sorter = self.create_patch_sorter(current_config, sort_algorithm)
        expected = [JsonChange(jsonpatch.JsonPatch([OperationWrapper().create(OperationType.REPLACE, "", target_config)]))]

        # Act
        actual = patch_sorter.sort(any_patch)

        # Assert
        self.assertEqual(expected, actual)

    def create_patch_sorter(self, config=None, sort_algorithm=None):
        if config is None:
            config=Files.CROPPED_CONFIG_DB_AS_JSON
        config_wrapper = self.config_wrapper
        config_wrapper.get_config_db_as_json = MagicMock(return_value=config)
        patch_wrapper = PatchWrapper(config_wrapper)
        operation_wrapper = OperationWrapper()
        path_addressing= ps.PathAddressing(config_wrapper)
        sort_algorithm_factory = ps.SortAlgorithmFactory(operation_wrapper, config_wrapper, path_addressing)
        if sort_algorithm:
            sort_algorithm_factory.create = MagicMock(return_value=sort_algorithm)

        return ps.PatchSorter(config_wrapper, patch_wrapper, sort_algorithm_factory)

class TestChangeWrapper(unittest.TestCase):
    def setUp(self):
        config_splitter = ps.ConfigSplitter(ConfigWrapper(), [])
        self.wrapper = ps.ChangeWrapper(PatchWrapper(), config_splitter)

    def test_adjust_changes(self):
        def check(changes, assumed, remaining, expected):
            actual = self.wrapper.adjust_changes(changes, assumed, remaining)
            self.assertEqual(len(expected), len(actual))

            for idx in range(len(expected)):
                self.assertCountEqual(expected[idx].patch, actual[idx].patch, f"JsonChange idx {idx} did not match")

        check([], {}, {}, [])
        # Add table to empty config
        check(changes=[JsonChange(jsonpatch.JsonPatch([{"op":"add", "path":"/TABLE1", "value":{}}]))],
              assumed={},
              remaining={},
              expected=[JsonChange(jsonpatch.JsonPatch([{"op":"add", "path":"/TABLE1", "value":{}}]))])
        # Add table, while tables exist in assumed and remaining
        check(changes=[JsonChange(jsonpatch.JsonPatch([{"op":"add", "path":"/TABLE3", "value":{}}]))],
              assumed={"TABLE1":{}},
              remaining={"TABLE2":{}},
              expected=[JsonChange(jsonpatch.JsonPatch([{"op":"add", "path":"/TABLE3", "value":{}}]))])
        # Add table with single field, while table has multiple fields in remaining
        check(changes=[JsonChange(jsonpatch.JsonPatch([{"op":"add", "path":"/TABLE3", "value":{"key3":"value3"}}]))],
              assumed={"TABLE1":{}},
              remaining={"TABLE2":{}, "TABLE3":{"key1":"value1", "key2":"value2"}},
              expected=[JsonChange(jsonpatch.JsonPatch([{"op":"add", "path":"/TABLE3/key3", "value":"value3"}]))])
        # Remove table to empty the config
        check(changes=[JsonChange(jsonpatch.JsonPatch([{"op":"remove", "path":"/TABLE1"}]))],
              assumed={"TABLE1":{}},
              remaining={},
              expected=[JsonChange(jsonpatch.JsonPatch([{"op":"remove", "path":"/TABLE1"}]))])
        # Remove table, while other tables exist in assumed and remaining
        check(changes=[JsonChange(jsonpatch.JsonPatch([{"op":"remove", "path":"/TABLE3"}]))],
              assumed={"TABLE1":{}, "TABLE3":{}},
              remaining={"TABLE2":{}},
              expected=[JsonChange(jsonpatch.JsonPatch([{"op":"remove", "path":"/TABLE3"}]))])
        # Remove table with single field, while table has multiple fields in remaining
        check(changes=[JsonChange(jsonpatch.JsonPatch([{"op":"remove", "path":"/TABLE3"}]))],
              assumed={"TABLE1":{}, "TABLE3":{"key3":"value3"}},
              remaining={"TABLE2":{}, "TABLE3":{"key1":"value1", "key2":"value2"}},
              expected=[JsonChange(jsonpatch.JsonPatch([{"op":"remove", "path":"/TABLE3/key3"}]))])
        # Change that does nothing
        check(changes=[JsonChange(jsonpatch.JsonPatch([{"op":"replace", "path":"/TABLE1", "value":{}}]))],
              assumed={"TABLE1":{}},
              remaining={},
              expected=[JsonChange(jsonpatch.JsonPatch([]))])
        # Replace table that exist in remaining
        check(changes=[JsonChange(jsonpatch.JsonPatch(
                      [{"op":"replace", "path":"/TABLE2", "value":{"key3":"value3", "key4":"value4"}}]))],
              assumed={"TABLE1":{}, "TABLE2":{}},
              remaining={"TABLE2":{"key1":"value1", "key2":"value2"}},
              expected=[JsonChange(jsonpatch.JsonPatch(
                        [{"op":"add", "path":"/TABLE2/key3", "value":"value3"},
                         {"op":"add", "path":"/TABLE2/key4", "value":"value4"}]))])
        # Multiple changes
        check(changes=[JsonChange(jsonpatch.JsonPatch([{"op":"replace", "path":"/TABLE1", "value":{}}])),
                       JsonChange(jsonpatch.JsonPatch([{"op":"add", "path":"/TABLE3", "value":{"key34":"value34"}}])),
                       JsonChange(jsonpatch.JsonPatch([{"op":"replace", "path":"/TABLE3", "value":{}}])),
                       JsonChange(jsonpatch.JsonPatch([{"op":"add", "path":"/TABLE3/key33", "value":"value33"}])),
                       JsonChange(jsonpatch.JsonPatch([{"op":"remove", "path":"/TABLE3"}]))],
              assumed={"TABLE1":{},"TABLE3":{}},
              remaining={"TABLE3":{"key31":"value31", "key32":"value32"}},
              expected=[JsonChange(jsonpatch.JsonPatch([])),
                        JsonChange(jsonpatch.JsonPatch([{"op":"add", "path":"/TABLE3/key34", "value":"value34"}])),
                        JsonChange(jsonpatch.JsonPatch([{"op":"remove", "path":"/TABLE3/key34"}])),
                        JsonChange(jsonpatch.JsonPatch([{"op":"add", "path":"/TABLE3/key33", "value":"value33"}])),
                        JsonChange(jsonpatch.JsonPatch([{"op":"remove", "path":"/TABLE3/key33"}]))])

class TestConfigSplitter(unittest.TestCase):
    def test_split_yang_non_yang_distinct_field_path(self):
        def check(config, expected_yang, expected_non_yang, ignore_paths_list=[], ignore_tables_without_yang=False):
            config_wrapper = ConfigWrapper()
            inner_config_splitters = []
            if ignore_tables_without_yang:
                inner_config_splitters.append(ps.TablesWithoutYangConfigSplitter(config_wrapper))
            if ignore_paths_list:
                inner_config_splitters.append(ps.IgnorePathsFromYangConfigSplitter(ignore_paths_list, config_wrapper))

            # ConfigWrapper() loads yang models from YANG_DIR
            splitter = ps.ConfigSplitter(ConfigWrapper(), inner_config_splitters)
            actual_yang, actual_non_yang = splitter.split_yang_non_yang_distinct_field_path(config)

            self.assertDictEqual(expected_yang, actual_yang)
            self.assertDictEqual(expected_non_yang, actual_non_yang)

        # test no flags
        check({}, {}, {})
        check(config={"ACL_TABLE":{"key1":"value1"}, "NON_YANG":{"key2":"value2"}, "VLAN":{"key31":"value31"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              expected_yang={"ACL_TABLE":{"key1":"value1"}, "VLAN":{"key31":"value31"}, "NON_YANG":{"key2":"value2"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              expected_non_yang={})

        # test ignore_tables_without_yang
        check({}, {}, {}, [], True)
        self.assertRaises(ValueError, check, {"ACL_TABLE":{}}, {"ACL_TABLE":{}}, {}, [], True) # ACL_TABLE has YANG model
        check({"ACL_TABLE":{"key1":"value1"}}, {"ACL_TABLE":{"key1":"value1"}}, {}, [], True)
        self.assertRaises(ValueError, check, {"ACL_TABLE":{}, "NON_YANG":{}}, {"ACL_TABLE":{}}, {"NON_YANG":{}},[], True)
        check(config={"ACL_TABLE":{"key1":"value1"}, "NON_YANG":{"key2":"value2"}, "VLAN":{"key31":"value31"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              expected_yang={"ACL_TABLE":{"key1":"value1"}, "VLAN":{"key31":"value31"}},
              expected_non_yang={"NON_YANG":{"key2":"value2"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              ignore_tables_without_yang=True)

        # test ignore_paths_list
        check({}, {}, {}, [""])
        self.assertRaises(ValueError, check, {"ACL_TABLE":{}}, {"ACL_TABLE":{}}, {}, ["/VLAN"]) # VLAN has YANG model
        self.assertRaises(ValueError, check, {"ACL_TABLE":{}}, {}, {"ACL_TABLE":{}}, ["/ACL_TABLE"])
        check({"ACL_TABLE":{"key1":"value1"}}, {}, {"ACL_TABLE":{"key1":"value1"}}, ["/ACL_TABLE"])
        check({"ACL_TABLE":{"key1":"value1"}}, {}, {"ACL_TABLE":{"key1":"value1"}}, ["/ACL_TABLE/key1"])
        check(config={"NON_YANG":{"key1":"value1"},"ACL_TABLE":{"key2":"value2"}},
              expected_yang={"NON_YANG":{"key1":"value1"}},
              expected_non_yang={"ACL_TABLE":{"key2":"value2"}},
              ignore_paths_list= ["/ACL_TABLE"])
        check(config={"ACL_TABLE":{"key1":"value1"}, "VLAN":{"key31":"value31"}, "NON_YANG":{"key2":"value2"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              expected_yang={"NON_YANG":{"key2":"value2"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              expected_non_yang={"ACL_TABLE":{"key1":"value1"}, "VLAN":{"key31":"value31"}},
              ignore_paths_list=["/VLAN/key31", "/ACL_TABLE"])
        check(config={"ACL_TABLE":{"key1":"value1"}, "NON_YANG":{"key2":"value2"}, "VLAN":{"key31":"value31"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              expected_yang={},
              expected_non_yang={"ACL_TABLE":{"key1":"value1"}, "VLAN":{"key31":"value31"}, "NON_YANG":{"key2":"value2"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              ignore_paths_list=["/VLAN/key31", "", "/ACL_TABLE"])

        # test ignore_paths_list and ignore_tables_without_yang
        check({}, {}, {}, [""])
        self.assertRaises(ValueError, check, {"ACL_TABLE":{}}, {"ACL_TABLE":{}}, {}, ["/VLAN"], True) # VLAN has YANG model
        self.assertRaises(ValueError, check, {"ACL_TABLE":{}}, {}, {"ACL_TABLE":{}}, ["/ACL_TABLE"], True)
        check({"ACL_TABLE":{"key1":"value1"}}, {}, {"ACL_TABLE":{"key1":"value1"}}, ["/ACL_TABLE"], True)
        check({"ACL_TABLE":{"key1":"value1"}}, {}, {"ACL_TABLE":{"key1":"value1"}}, ["/ACL_TABLE/key1"], True)
        check(config={"NON_YANG":{"key1":"value1"},"ACL_TABLE":{"key2":"value2"}},
              expected_yang={},
              expected_non_yang={"NON_YANG":{"key1":"value1"},"ACL_TABLE":{"key2":"value2"}},
              ignore_paths_list= ["/ACL_TABLE"],
              ignore_tables_without_yang=True)
        check(config={"ACL_TABLE":{"key1":"value1"}, "NON_YANG":{"key2":"value2"}, "VLAN":{"key31":"value31"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              expected_yang={},
              expected_non_yang={"ACL_TABLE":{"key1":"value1"}, "VLAN":{"key31":"value31"}, "NON_YANG":{"key2":"value2"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              ignore_paths_list=["/VLAN/key31", "/ACL_TABLE"],
              ignore_tables_without_yang=True)
        check(config={"ACL_TABLE":{"key1":"value1"}, "NON_YANG":{"key2":"value2"}, "VLAN":{"key31":"value31"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              expected_yang={},
              expected_non_yang={"ACL_TABLE":{"key1":"value1"}, "VLAN":{"key31":"value31"}, "NON_YANG":{"key2":"value2"}, "ANOTHER_NON_YANG":{"key41":"value41"}},
              ignore_paths_list=["/VLAN/key31", "", "/ACL_TABLE"],
              ignore_tables_without_yang=True)

    def test_merge_configs_with_distinct_field_path(self):
        def check(config1, config2, expected=None):
            splitter = ps.ConfigSplitter(ConfigWrapper(), [])

            # merging config1 and config2
            actual = splitter.merge_configs_with_distinct_field_path(config1, config2)
            self.assertDictEqual(expected, actual)

            # merging config2 and config1 - should be the same result
            actual = splitter.merge_configs_with_distinct_field_path(config2, config1)
            self.assertDictEqual(expected, actual)

        check({}, {}, {})
        check({"TABLE1":{}}, {}, {"TABLE1":{}})
        check({"TABLE1":{}}, {"TABLE2": {}}, {"TABLE1":{}, "TABLE2":{}})
        check({"TABLE1":{"key1": "value1"}}, {}, {"TABLE1":{"key1": "value1"}})
        check({"TABLE1":{"key1": "value1"}}, {"TABLE1":{}}, {"TABLE1":{"key1": "value1"}})
        check({"TABLE1":{"key1": "value1"}},
              {"TABLE1":{"key2": "value2"}},
              {"TABLE1":{"key1": "value1", "key2": "value2"}})
        # keys the same
        self.assertRaises(ValueError, check, {"TABLE1":{"key1": "value1"}}, {"TABLE1":{"key1": "value2"}})

class TestNonStrictPatchSorter(unittest.TestCase):
    def test_sort__invalid_yang_covered_config__failure(self):
        # Arrange
        sorter = self.__create_patch_sorter(valid_yang_covered_config=False)

        # Act and assert
        self.assertRaises(ValueError, sorter.sort, Files.MULTI_OPERATION_CONFIG_DB_PATCH)

    def test_sort__invalid_yang_covered_config_patch_updating_tables_without_yang__failure(self):
        # Arrange
        sorter = self.__create_patch_sorter(valid_patch_only_tables_with_yang_models=False)

        # Act and assert
        self.assertRaises(ValueError, sorter.sort, Files.MULTI_OPERATION_CONFIG_DB_PATCH)

    def test_sort__no_errors_algorithm_specified__calls_inner_patch_sorter(self):
        # Arrange
        patch = Mock()
        algorithm = Mock()
        non_yang_changes = [Mock()]
        yang_changes = [Mock(), Mock()]
        expected = non_yang_changes + yang_changes
        sorter = self.__create_patch_sorter(patch, algorithm, non_yang_changes, yang_changes)

        # Act
        actual = sorter.sort(patch, algorithm)

        # Assert
        self.assertListEqual(expected, actual)

    def test_sort__no_errors_algorithm_not_specified__calls_inner_patch_sorter(self):
        # Arrange
        patch = Mock()
        non_yang_changes = [Mock()]
        yang_changes = [Mock(), Mock()]
        expected = non_yang_changes + yang_changes
        sorter = self.__create_patch_sorter(patch, None, non_yang_changes, yang_changes)

        # Act
        actual = sorter.sort(patch)

        # Assert
        self.assertListEqual(expected, actual)

    def __create_patch_sorter(self,
                              patch=None,
                              any_algorithm=None,
                              any_adjusted_changes_non_yang=None,
                              any_adjusted_changes_yang=None,
                              valid_yang_covered_config=True,
                              valid_patch_only_tables_with_yang_models=True):
        ignore_paths_list = Mock()
        config_wrapper = Mock()
        patch_wrapper = Mock()
        inner_patch_sorter = Mock()
        change_wrapper = Mock()
        config_splitter = Mock()

        patch = patch if patch else Mock()
        any_algorithm = any_algorithm if any_algorithm else ps.Algorithm.DFS
        any_current_config = Mock()
        any_target_config = Mock()
        any_current_config_yang = Mock()
        any_current_config_non_yang = Mock()
        any_target_config_yang = Mock()
        any_target_config_non_yang = Mock()
        any_patch_non_yang = jsonpatch.JsonPatch([{"op":"add", "path":"/NON_YANG_TABLE", "value":{}}])
        any_patch_yang = Mock()
        any_changes_yang = [Mock()]
        any_changes_non_yang = [JsonChange(any_patch_non_yang)]

        config_wrapper.get_config_db_as_json.side_effect = \
            [any_current_config]

        patch_wrapper.simulate_patch.side_effect = \
            create_side_effect_dict(
                {(str(patch), str(any_current_config)):
                    any_target_config})

        config_splitter.split_yang_non_yang_distinct_field_path.side_effect = \
            create_side_effect_dict(
                {(str(any_current_config),): (any_current_config_yang, any_current_config_non_yang),
                 (str(any_target_config),): (any_target_config_yang, any_target_config_non_yang)})

        config_wrapper.validate_config_db_config.side_effect = \
            create_side_effect_dict({(str(any_target_config_yang),): valid_yang_covered_config})

        patch_wrapper.generate_patch.side_effect = \
            create_side_effect_dict(
                {(str(any_current_config_non_yang), str(any_target_config_non_yang)): any_patch_non_yang,
                 (str(any_current_config_yang), str(any_target_config_yang)): any_patch_yang})

        patch_wrapper.validate_config_db_patch_has_yang_models.side_effect = \
            create_side_effect_dict(
                {(str(any_patch_yang),): valid_patch_only_tables_with_yang_models})

        inner_patch_sorter.sort.side_effect = \
            create_side_effect_dict(
                {(str(any_patch_yang), str(any_algorithm), str(any_current_config_yang)): any_changes_yang})

        change_wrapper.adjust_changes.side_effect = \
            create_side_effect_dict(
                {(str(any_changes_non_yang), str(any_current_config_non_yang), str(any_current_config_yang)): any_adjusted_changes_non_yang,
                 (str(any_changes_yang), str(any_current_config_yang), str(any_target_config_non_yang)): any_adjusted_changes_yang})

        return ps.NonStrictPatchSorter(config_wrapper, patch_wrapper, config_splitter, change_wrapper, inner_patch_sorter)

class TestStrictPatchSorter(unittest.TestCase):
    def test_sort__patch_updating_tables_without_yang__failure(self):
        # Arrange
        patch = Mock()
        sorter = self.__create_patch_sorter(patch, valid_patch_only_tables_with_yang_models=False)

        # Act and assert
        self.assertRaises(ValueError, sorter.sort, patch)

    def test_sort__target_config_not_valid_according_to_yang__failure(self):
        # Arrange
        patch = Mock()
        sorter = self.__create_patch_sorter(patch, valid_config_db=False)

        # Act and assert
        self.assertRaises(ValueError, sorter.sort, patch)

    def test_sort__no_errors_algorithm_specified__calls_inner_patch_sorter(self):
        # Arrange
        patch = Mock()
        algorithm = Mock()
        changes = [Mock(), Mock(), Mock()]
        sorter = self.__create_patch_sorter(patch, algorithm, changes)

        # Act
        actual = sorter.sort(patch, algorithm)

        # Assert
        self.assertListEqual(changes, actual)

    def test_sort__no_errors_algorithm_not_specified__calls_inner_patch_sorter(self):
        # Arrange
        patch = Mock()
        changes = [Mock(), Mock(), Mock()]
        sorter = self.__create_patch_sorter(patch, None, changes)

        # Act
        actual = sorter.sort(patch)

        # Assert
        self.assertListEqual(changes, actual)

    def __create_patch_sorter(self,
                              patch=None,
                              algorithm=None,
                              changes=None,
                              valid_patch_only_tables_with_yang_models=True,
                              valid_config_db=True):
        config_wrapper = Mock()
        patch_wrapper = Mock()
        inner_patch_sorter = Mock()

        any_current_config = Mock()
        any_target_config = Mock()
        patch = patch if patch else Mock()
        algorithm = algorithm if algorithm else ps.Algorithm.DFS

        config_wrapper.get_config_db_as_json.side_effect = \
            [any_current_config, any_target_config]

        patch_wrapper.simulate_patch.side_effect = \
            create_side_effect_dict(
                {(str(patch), str(any_current_config)):
                    any_target_config})

        patch_wrapper.validate_config_db_patch_has_yang_models.side_effect = \
            create_side_effect_dict(
                {(str(patch),): valid_patch_only_tables_with_yang_models})

        config_wrapper.validate_config_db_config.side_effect = \
            create_side_effect_dict(
                {(str(any_target_config),): valid_config_db})


        inner_patch_sorter.sort.side_effect = \
            create_side_effect_dict(
                {(str(patch), str(algorithm)): changes})

        return ps.StrictPatchSorter(config_wrapper, patch_wrapper, inner_patch_sorter)
