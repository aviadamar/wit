# Reupload
import filecmp
import os


def differentiate(path):
    """Returns dict indicate directories and files in a given path."""
    files = {'path': path, 'dirs': [], 'files': []}
    list_dir = os.listdir(path)
    for file in list_dir:
        if os.path.isdir(os.path.join(path, file)):
            files['dirs'].append(file)
        else:
            files['files'].append(file)
    return files


def get_report(report):
    for key, value in report.items():
        print(f"{key.upper()}:")
        if key != 'equal':
            for item in value:
                print(f"\t{chr(9205)}{item}")
        else:
            print(f"\t{chr(9205)}{value}\n")
    print("-" * 70)


def dirs_comparison(*args):
    """Function compare between two given directories.

    The function returns a dictionart 'report' indicates the comperison results.
    report dict attributes:
        'dits': Indicates the paths of the full path of the given directories.
        'diffrent_dirs': set of names indicates uncommon directories.
        ' diffrent_files': set of names indicates uncommon files.
                           if two files has the same name but they are diffrent
                           the file will apeare as full path.
        'common_dirs' : set of names indicates common directories.
        'common_files': set of names indicates common files.
        'equal': boolean indicates if the two directories are equal or not.
    """
    report = {'dirs': None, 'diffrent_dirs': set(), 'diffrent_files': set(
    ), 'common_dirs': set(), 'common_files': set(), 'equal': None}
    dirs_contents = []
    for path in args:
        dirs_contents.append(differentiate(path))

    #  Paths
    report['dirs'] = [d['path'] for d in dirs_contents]

    #  Dirs
    set1 = set(dirs_contents[0]['dirs'])
    set2 = set(dirs_contents[1]['dirs'])
    report['common_dirs'] = set1.intersection(set2)
    report['diffrent_dirs'] = set1.difference(
        set2).union(set2. difference(set1))

    #  Files
    set1 = set(dirs_contents[0]['files'])
    set2 = set(dirs_contents[1]['files'])
    report['diffrent_files'] = set1.difference(
        set2).union(set2. difference(set1))
    common_files_to_check = set1.intersection(set2)
    for file in common_files_to_check:
        file1 = os.path.join(dirs_contents[0]['path'], file)
        file2 = os.path.join(dirs_contents[1]['path'], file)
        if filecmp.cmp(file1, file2):
            report['common_files'].update({file})
        else:
            report['diffrent_files'].update({file1, file2})

    report['equal'] = not report['diffrent_dirs'] and not report['diffrent_files']
    return report


def deep_comparison(dir1, dir2, getreport=None):
    """Recursively checks whether two directories are equal.

    The function checks all directories and subdirectories.
    """
    report = dirs_comparison(dir1, dir2)
    if getreport is not None:
        get_report(report)
    if not report['equal']:
        return [False, report]
    if len(report['common_dirs']) == 0:
        return [True, report]
    for d in report['common_dirs']:
        dir1 = os.path.join(dir1, d)
        dir2 = os.path.join(dir2, d)
        return deep_comparison(dir1, dir2, getreport=getreport)
