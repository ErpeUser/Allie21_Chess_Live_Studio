"""Exercise explicit cache setup without loading Torch or downloading weights."""
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))


def setup_module_under_test():
    return importlib.import_module('model_setup')


def snapshot(tmp_path):
    (tmp_path / 'config.json').write_text(json.dumps({'model_type': 'allie'}))
    # A small fixture is sufficient: setup checks completeness, not inference.
    (tmp_path / 'model.safetensors').write_bytes(b'fixture-weights')
    return tmp_path


def test_offline_check_never_requests_remote_files(tmp_path):
    module = setup_module_under_test()
    downloader = Mock(return_value=str(snapshot(tmp_path)))
    with patch.dict(sys.modules, {'huggingface_hub': SimpleNamespace(snapshot_download=downloader)}):
        assert module.prepare_model(download=False) == tmp_path
    options = downloader.call_args.kwargs
    assert options['local_files_only'] is True
    assert options['revision'] == 'd2545701ff5af46a51ac947911844f779b355a08'
    assert options['repo_id'] == 'yimingzhang/allie-2.1'
    assert options['allow_patterns'] == ['config.json', 'model.safetensors']
    assert 'trust_remote_code' not in options


def test_explicit_download_only_fetches_pinned_model_data(tmp_path):
    module = setup_module_under_test()
    downloader = Mock(return_value=str(snapshot(tmp_path)))
    with patch.dict(sys.modules, {'huggingface_hub': SimpleNamespace(snapshot_download=downloader)}):
        module.prepare_model(download=True)
    assert downloader.call_args.kwargs['local_files_only'] is False
    assert downloader.call_args.kwargs['allow_patterns'] == ['config.json', 'model.safetensors']


def test_partial_cache_not_reported_ready(tmp_path):
    module = setup_module_under_test()
    (tmp_path / 'config.json').write_text('{"model_type":"allie"}')
    downloader = Mock(return_value=str(tmp_path))
    with patch.dict(sys.modules, {'huggingface_hub': SimpleNamespace(snapshot_download=downloader)}), pytest.raises(RuntimeError, match='model.safetensors'):
        module.prepare_model(download=False)


def test_bad_config_not_reported_ready(tmp_path):
    module = setup_module_under_test()
    snapshot(tmp_path)
    (tmp_path / 'config.json').write_text('[]')
    downloader = Mock(return_value=str(tmp_path))
    with patch.dict(sys.modules, {'huggingface_hub': SimpleNamespace(snapshot_download=downloader)}), pytest.raises(RuntimeError, match='config'):
        module.prepare_model(download=False)


def test_cli_failure_has_nonzero_exit_and_no_sensitive_exception(capsys):
    module = setup_module_under_test()
    with patch.object(module, 'prepare_model', side_effect=OSError('token=private-secret')):
        assert module.main([]) == 1
    output = capsys.readouterr()
    assert 'private-secret' not in output.out + output.err
    assert '--download' in output.err


def test_cli_default_is_offline(tmp_path):
    module = setup_module_under_test()
    with patch.object(module, 'prepare_model', return_value=tmp_path) as prepare:
        assert module.main([]) == 0
    prepare.assert_called_once_with(download=False)
