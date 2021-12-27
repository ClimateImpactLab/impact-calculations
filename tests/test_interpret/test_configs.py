import pytest
import unittest
from pathlib import Path
from interpret import configs
from interpret.configs import merge_import_config, get_covariate_rate

class TestMergeImportConfig:
    """Collection of tests for merge_import_config
    """

    def test_no_import(self):
        """Test that returns input config when no 'import:'"""
        input_dict = {"a": 123, "b": 456}
        expected = input_dict.copy()

        output = merge_import_config(input_dict, fpath="")
        assert expected == dict(output.items())

    def test_import_absolutepath(self, tmpdir):
        """Test that imports absolute path, input configs over-rides import configs"""
        import_config = tmpdir.join("import_config.yml")
        import_config.write("a: 789\nalist:\n  - item1\n")

        input_dict = {"a": 123, "b": 456, "import": str(import_config)}
        expected = {"a": 123, "b": 456, "alist": ["item1"]}

        output = merge_import_config(input_dict, fpath="")
        assert expected == dict(output.items())

    def test_import_relativepath(self, tmpdir):
        """Test that imports relative to input config path, input configs overrides import configs"""
        base_path = str(tmpdir)  # Pretend that our input config is within this dir

        import_config = tmpdir.join("import_config.yml")
        import_config.write("a: 789\nalist:\n  - item1\n")
        import_config_relpath = Path(str(import_config)).relative_to(base_path)

        input_dict = {"a": 123, "b": 456, "import": import_config_relpath}
        expected = {"a": 123, "b": 456, "alist": ["item1"]}

        output = merge_import_config(input_dict, fpath=base_path)
        assert expected == dict(output.items())

    def test_nested_import(self, tmpdir):
        """Test that resolves 'import:' in imported config."""
        base_path = str(tmpdir)  # Pretend that our input config is within this dir

        # First imported config.
        import_config = tmpdir.join("import_config.yml")
        import_config.write("import: import_config2.yml\na: 789\nalist:\n  - item1\n")

        # 2nd imported config, imported by first imported config.
        import_config2 = tmpdir.join("import_config2.yml")
        import_config2.write("z: foobar\n")

        import_config_relpath = Path(str(import_config)).relative_to(base_path)

        input_dict = {"a": 123, "b": 456, "import": import_config_relpath}
        expected = {"a": 123, "b": 456, "alist": ["item1"], "z": "foobar"}

        output = merge_import_config(input_dict, fpath=base_path)
        assert expected == dict(output.items())


class TestConfigCovariateChange(unittest.TestCase):
    def test_get_covariate_rate_ambiguous(self):

        ambiguous_config = {'slowadapt': 'both', 'scale-covariate-changes': {'income': 0.5, 'climate': 0.5}}
        with pytest.raises(ValueError):
            get_covariate_rate(ambiguous_config, 'income')

    def test_get_covariate_rate_slowadapt(self):

        self.assertEqual(get_covariate_rate({'slowadapt': 'income'}, 'income'), 0.5)
        self.assertEqual(get_covariate_rate({'slowadapt': 'income'}, 'climate'), 1)
        self.assertEqual(get_covariate_rate({'slowadapt': 'both'}, 'income'), 0.5)
        self.assertEqual(get_covariate_rate({'slowadapt': 'both'}, 'climate'), 0.5)

    def test_get_covariate_rate_arbitrary_scalar(self):

        config = {'scale-covariate-changes': {'income': 0.7, 'climate': 4}}
        self.assertEqual(get_covariate_rate(config, 'income'), 0.7)
        self.assertEqual(get_covariate_rate(config, 'climate'), 4)

    def test_get_covariate_rate_nosideeffect(self):

        config = {'scale-covariate-changes': {'income': 0.7, 'climate': 4}, 'stuff': 'random'}
        rate = get_covariate_rate(config, 'income')
        self.assertTrue('stuff' in config and config.get('stuff') == 'random')

class TestConfigUsage(unittest.TestCase):
    def test_config_dict(self):
        config = {'ignored1': 0, 'used': 1, 'inparent1': 2, 'dict': {'inchild': 3, 'ignored2': 0}, 'inparent2': 4, 'list': ['ignored3', {'inlistdict': 5, 'ignored4': 0}]}
        config = configs.standardize(config)

        # Make sure I can access all non-ignored entries
        self.assertEqual(config['used'], 1)
        subconfig = configs.merge(config, 'dict')
        self.assertEqual(subconfig['inchild'], 3)
        self.assertEqual(subconfig['inparent1'], 2)
        subconfig = configs.merge(config, config['list'][1])
        self.assertEqual(subconfig['inlistdict'], 5)
        self.assertEqual(subconfig['inparent2'], 4)

        missing = config.check_usage()
        self.assertEqual(missing, set(['ignored1', 'dict.ignored2', 'list.0', 'list.1.ignored4']))
