project('vidyarthi', version: '0.1.0',
  license: 'GPL-2.0-or-later',
  meson_version: '>= 0.62.0',
)

py = import('python').find_installation('python3')

blueprint_compiler = find_program('blueprint-compiler', required: true)

datadir = get_option('datadir')
vidyarthi_dir = datadir / 'shikshan' / 'vidyarthi'

# Compile Blueprint UI files to XML
ui_files = custom_target(
  'window.ui',
  input:   'data/ui/window.blp',
  output:  'window.ui',
  command: [blueprint_compiler, 'compile', '--output', '@OUTPUT@', '@INPUT@'],
  install: true,
  install_dir: vidyarthi_dir / 'data' / 'ui',
)

# Install Python sources — GTK frontend + GTK-free core (SMO-0611..0613)
py.install_sources(
  [
    'src/main.py',
    'src/window.py',
    'src/catalog.py',
    'src/engine_client.py',
    'src/session.py',
    'src/xapi.py',
    'src/runner.py',
  ],
  subdir: 'shikshan/vidyarthi/src',
)

# SQL engine binary + sandbox profiles (SMO-0560/0570)
install_data(
  [
    'engines/sql/main.py',
    'engines/sql/sandbox.bwrap',
    'engines/sql/seccomp.json',
  ],
  install_dir: vidyarthi_dir / 'engines' / 'sql',
)

# modulectl library (SMO-0580)
install_data(
  [
    'modulectl/__init__.py',
    'modulectl/verify.py',
    'modulectl/install.py',
  ],
  install_dir: vidyarthi_dir / 'modulectl',
)

# Install data
install_data(
  'data/ui/window.blp',
  install_dir: vidyarthi_dir / 'data' / 'ui',
)
