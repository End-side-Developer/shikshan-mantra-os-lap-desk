project('vidyarthi', version: '0.1.0',
  license: 'GPL-2.0-or-later',
  meson_version: '>= 0.62.0',
)

py = import('python').find_installation('python3')

blueprint_compiler = find_program('blueprint-compiler', required: true)

# Compile Blueprint UI files to XML
ui_files = custom_target(
  'window.ui',
  input:   'data/ui/window.blp',
  output:  'window.ui',
  command: [blueprint_compiler, 'compile', '--output', '@OUTPUT@', '@INPUT@'],
  install: true,
  install_dir: get_option('datadir') / 'shikshan' / 'vidyarthi' / 'data' / 'ui',
)

# Install Python sources
py.install_sources(
  [
    'src/main.py',
    'src/window.py',
  ],
  subdir: 'shikshan/vidyarthi/src',
)

# Install data
install_data(
  'data/ui/window.blp',
  install_dir: get_option('datadir') / 'shikshan' / 'vidyarthi' / 'data' / 'ui',
)
