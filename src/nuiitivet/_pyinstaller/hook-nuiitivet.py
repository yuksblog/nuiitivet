from PyInstaller.utils.hooks import collect_data_files

from nuiitivet._pyinstaller import excluded_imports, hidden_imports, matplotlib_installed

datas = collect_data_files("nuiitivet")
hiddenimports = hidden_imports(with_matplotlib=matplotlib_installed())
excludedimports = excluded_imports(with_matplotlib=matplotlib_installed())
