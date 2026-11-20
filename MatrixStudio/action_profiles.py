"""Reviewed action presets and architecture-safe adapter routing."""
import json
from pathlib import Path

APP = Path(__file__).resolve().parent
ADAPTERS = json.loads((APP / 'action_adapters.json').read_text(encoding='utf-8'))
NAMES = {a['key']: Path(a['file']).name for a in ADAPTERS}
PRESETS = json.loads((APP / 'action_presets.json').read_text(encoding='utf-8'))


def prepare_action(data):
    data = dict(data)
    key = str(data.get('preset', 'manual'))
    if key != 'manual':
        preset = next((p for p in PRESETS if p['id'] == key), None)
        if preset is None:
            raise ValueError('Selecciona un preset de acción válido.')
        for field in ('family', 'profile'):
            if field in data and data[field] != preset['settings'][field]:
                raise ValueError('El preset requiere su motor y perfil. Elige Manual para cambiarlos.')
        data = {**preset['settings'], **data}
        # Adapter names are selected by reviewed preset, never by file path.
        for field in ('adapter', 'action_lora'):
            data[field] = preset['settings'][field]
        if not str(data.get('prompt', '')).strip():
            data['prompt'] = preset['prompt']
    return data


def validate_adapters(p):
    adapter, action = p.get('adapter', 'none'), p.get('action_lora', 'none')
    if adapter not in ('none', 'motion_fix') or action not in ('none', 'kungfu', 'punch'):
        raise ValueError('Adaptador de acción desconocido.')
    if adapter == 'motion_fix' and (p['family'] != 'wan14b' or p['profile'] != 'fast'):
        raise ValueError('Slow-Mo Fix requiere Wan 14B y el perfil de cuatro pasos.')
    if action == 'kungfu' and p['family'] != 'wan14b' or action == 'punch' and p['family'] != 'wan5b':
        raise ValueError('La LoRA no corresponde a la arquitectura del modelo.')
    strength = float(p.get('action_strength', 1))
    if not 0 <= strength <= 1.5:
        raise ValueError('Intensidad LoRA: 0–1.5.')
    return strength


def adapter_keys(p):
    keys = ['motion_fix_high', 'motion_fix_low'] if p.get('adapter') == 'motion_fix' else []
    if p.get('action_lora') == 'kungfu':
        keys += ['kungfu_high', 'kungfu_low']
    elif p.get('action_lora') == 'punch':
        keys += ['punch']
    return keys


def required_adapters(p):
    keys = adapter_keys(p)
    return [a for a in ADAPTERS if a['key'] in keys]


def preset_status(root):
    return [{**p, 'ready': all((root / 'Data/Models' / a['folder'] / Path(a['file']).name).is_file()
            for a in required_adapters(p['settings']))} for p in PRESETS]
