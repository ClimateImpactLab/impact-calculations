from pathlib import Path
from interpret.configs import merge_import_config


class TestMergeImportConfig:
    """Collection of tests for merge_import_config
    """

    def test_no_import(self):
        """Test that returns input config when no 'import:'"""
        input_dict = {"a": 123, "b": 456}
        expected = input_dict.copy()

        output = merge_import_config(input_dict, fpath="")
        assert expected == output

    def test_import_absolutepath(self, tmpdir):
        """Test that imports absolute path, input configs over-rides import configs"""
        import_config = tmpdir.join("import_config.yml")
        import_config.write("a: 789\nalist:\n  - item1\n")

        input_dict = {"a": 123, "b": 456, "import": str(import_config)}
        expected = {"a": 123, "b": 456, "alist": ["item1"]}

        output = merge_import_config(input_dict, fpath="")
        assert expected == output

    def test_import_relativepath(self, tmpdir):
        """Test that imports relative to input config path, input configs overrides import configs"""
        base_path = str(tmpdir)  # Pretend that our input config is within this dir

        import_config = tmpdir.join("import_config.yml")
        import_config.write("a: 789\nalist:\n  - item1\n")
        import_config_relpath = Path(str(import_config)).relative_to(base_path)

        input_dict = {"a": 123, "b": 456, "import": import_config_relpath}
        expected = {"a": 123, "b": 456, "alist": ["item1"]}

        output = merge_import_config(input_dict, fpath=base_path)
        assert expected == output

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
        assert expected == output
