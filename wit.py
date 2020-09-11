from datetime import datetime
import os
import os.path
import random
import shutil  # copy files operations
import string
import sys
from typing import Any, Dict, List, Optional, Union

import dirscomparison  # A basic module I created for folders comparisons.
from graphviz import Digraph  # type: ignore
import pytz


BACKUP_DIR_NAME: str = '.wit'
WIT_METADATA_FILE: str = 'references.txt'
STAGING_AREA: str = 'staging_area'
IMAGES: str = 'images'
ACTIVATE_BRANCH: str = 'activated.txt'


def run_only_if_backup(f):
    """Decorator, will run function only if there is a backup directory in path."""
    def wrapper(*args, **kargs):
        if f.__name__ == 'add':
            full_path = is_abs_path(args[0], kargs['path'])
        else:
            full_path = kargs['path']
        backup_folder = find_directory(full_path)
        if backup_folder is not None:
            f(*args, **kargs, backup_folder=backup_folder, full_path=full_path)
    return wrapper


def init(*args: str, **kargs: str) -> None:
    """Creates initial folders for backup."""
    path: str = kargs['path']
    sub_folders: List[str] = [IMAGES, STAGING_AREA]
    create_folders(path, BACKUP_DIR_NAME)
    backup_folder_path = os.path.join(path, BACKUP_DIR_NAME)
    create_folders(backup_folder_path, *sub_folders)
    backup_directory_metadata(backup_folder_path)


def backup_directory_metadata(path: str) -> None:
    """Create the initial metadate for the backup folder."""
    file_path: str = os.path.join(path, WIT_METADATA_FILE)
    with open(file_path, 'w') as file:
        file.write("HEAD=None\nmaster=None")
    with open(os.path.join(path, ACTIVATE_BRANCH), 'w') as file:
        file.write('master')


def create_folders(path: str, *args: str) -> None:
    """Create new folders on given path.

    Args:
        path (str): Path destination to create the folders.
        args (tuple): Folder's names to create in given path.
    Returns:
        None.
    """
    os.chdir(path)
    for directory in args:
        new_path = os.path.join(path, directory)
        if not os.path.exists(new_path):
            os.mkdir(directory)


@run_only_if_backup
def add(*args: str, **kargs: str) -> None:
    """Adds files in given path to the neerest backup directory.

    Args:
        args (tuple): File \ directory name.
        kargs (dict): Path of current working directory.
    Returns:
        None.
    """
    backup_folder = kargs['backup_folder']
    full_path = kargs['full_path']
    relative_path = os.path.join(
        backup_folder, STAGING_AREA, args[0])

    if os.path.dirname(relative_path) != STAGING_AREA:
        os.makedirs(os.path.dirname(relative_path), exist_ok=True)
    copy_files(full_path, relative_path, inside=True)


def is_abs_path(path: str, cwd: str) -> str:
    if not os.path.isabs(path):
        return os.path.join(cwd, path)
    return path


def find_directory(path: str, name: str = BACKUP_DIR_NAME) -> Any:
    """The function returns a path if the directory name is in one of the parent folders.

    Args:
        path (str): An initial path to start the search with.
        name (str, optional): The directory name to look for.
    Returns:
        str: Path of the parent direcory.
        None: In case directory is not in the path root.
    """
    if os.path.isfile(path):
        path = os.path.dirname(path)
    if name in os.listdir(path):
        return os.path.join(path, name)
    if len(path.split(os.sep)) == 1:
        return None
    return find_directory(os.path.dirname(path))


def copy_files(copy_from: str, copy_to: str, inside=False) -> None:
    """Copy file or full path directory to a given destination directory.

    Args:
        copy_from (str): Path indicates what to copy
        copy_to   (str): Path indicates the copy destination directory.
        inside   (bool): Indicate if to copy into a new folder or directly to the given path.
    Returns:
        None.
    """
    if not inside:
        copy_to = os.path.join(copy_to, os.path.basename(copy_from))
    if os.path.isfile(copy_from):
        shutil.copy2(copy_from, copy_to)
    else:
        shutil.copytree(copy_from, copy_to, dirs_exist_ok=True)
    return None


def delete_dir(path: str, parent: bool = True) -> None:
    """Deletes a given directory.

    If parent is false, the function will delete only the dir content.
    """
    if not os.path.exists(path):
        return None
    shutil.rmtree(path)
    if not parent:
        os.makedirs(path, exist_ok=True)
    return None


def create_metadata(path: str, name: str, message: str, parent: Optional[str] = None) -> None:
    """Creates metadate for a file.

    Args:
        path (str): The path for the new file.
        name (str): The file name.
        message (str): The message contant.
        parent  (str): Indicate the previews commit id folder.
    Returns:
        None.
    """
    greenwich = pytz.timezone('GB')
    date = greenwich.localize(datetime.now())
    metadata = (
        f"parent={parent},\n"
        + f"date={date.strftime('%c %z')}\n"
        + f"message={message}"
    )
    file_path = os.path.join(path, f'{name}.txt')
    with open(file_path, 'w') as file:
        file.write(metadata)
    return None


def update_branch(path: str, branch: str, commit_id: str) -> None:
    """Update branch with new commit id."""
    with open(os.path.join(path, WIT_METADATA_FILE), 'r') as file:
        file_info = file.read().split('\n')

    is_found = False
    index = 0
    while index < len(file_info) and not is_found:
        line_parts = list(file_info[index].partition('='))
        if line_parts[0] == branch:
            line_parts[2] = commit_id
            file_info[index] = ''.join(line_parts)
            is_found = True
        index += 1

    with open(os.path.join(path, WIT_METADATA_FILE), 'w') as file:
        file.write('\n'.join(file_info))
    return None


def get_commit_info(path: str, head: str, file_type='.txt') -> Dict[str, str]:
    """Return dict contain all commit information by categories."""
    file_path = os.path.join(path, IMAGES, head + file_type)
    with open(file_path, 'r') as file:
        file_info = file.readlines()
    return dict([line.strip().split('=') for line in file_info])


@run_only_if_backup
def commit(*args: str, merge=None, **kargs: str) -> None:
    backup_folder = kargs['backup_folder']

    branch = is_branch(backup_folder, get_active_branch(backup_folder))
    head_directory = get_head(backup_folder)
    # print("HEAD:", head_directory)
    if head_directory == branch:
        update_branch(backup_folder, branch, head_directory)

    commit_id: str = generate_directory_name()
    message: str = ' '.join(args)
    image_path: str = os.path.join(backup_folder, IMAGES)

    if is_same_backup(backup_folder):  # BONUS
        return None

    if merge is None:
        parents = head_directory
    else:
        parents = ','.join([head_directory, merge])

    create_metadata(image_path, commit_id, message, parent=parents)
    update_backup_folder_metadata(backup_folder, commit_id)
    create_folders(image_path, commit_id)
    staging_path: str = os.path.join(backup_folder, STAGING_AREA)
    copy_files(staging_path, os.path.join(image_path, commit_id), inside=True)
    return None


def join_path(path: str, files: List[str]) -> List[str]:
    """Combines all file names with a given path."""
    return [os.path.join(path, file) for file in files]


def is_same_backup(backup_folder: str) -> bool:
    """Check if the last backup is equal to the next one."""
    head_directory = get_head(backup_folder)
    images_folder = os.path.join(backup_folder, IMAGES)
    last_backup_folder = os.path.join(images_folder, head_directory)
    if os.path.basename(last_backup_folder) == "None":
        return False

    staging_folder = os.path.join(backup_folder, STAGING_AREA)
    result = dirscomparison.deep_comparison(
        last_backup_folder, staging_folder)[0]
    return result


def get_head(path: str) -> str:
    """Returns the current head directory name."""
    with open(os.path.join(path, WIT_METADATA_FILE), 'r') as file:
        return file.readline().partition('=')[2].strip()


def get_master(path: str) -> str:
    """Returns the current master directory name."""
    with open(os.path.join(path, WIT_METADATA_FILE), 'r') as file:
        return file.readlines()[1].partition('=')[2].strip()


def is_commit_id_valid(backup_folder: str, commit_id: str) -> bool:
    """Check if a given commit id directory is exist."""
    path = os.path.join(backup_folder, IMAGES, commit_id)
    return os.path.exists(path)


def update_backup_folder_metadata(path: str, commit_id: str, checkout=False) -> None:
    """Updates the backup folder metadata."""

    head = get_head(path)
    master = get_master(path)
    if not checkout:
        if head == master and get_active_branch(path) == 'master':
            master = commit_id

    reference_path = os.path.join(path, WIT_METADATA_FILE)
    with open(reference_path, 'r') as file:
        current_info = [line.strip() for line in file.readlines()[2:]]

    with open(reference_path, 'w') as file:
        file.write(
            f"HEAD={commit_id}\n"
            + f"master={master}\n"
            + '\n'.join(current_info)
        )
    return None


def generate_directory_name(n: int = 40) -> str:
    """Generate a random folder name in a given length."""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for i in range(n))


def print_list(*args) -> None:
    """Prints list items.

    If an items apears to be empty/false a None string will be printed."""
    if args:
        for line in args:
            if line:
                print(f"\t-> {line}")
            else:
                print("\t-> None")
    else:
        print("\t-> None")
    return None


def Changes_to_be_committed(head_directory: str, backup_folder: str) -> Dict[str, Union[str, bool]]:
    """Returns all the files in staging area and not in last image folder."""
    last_image = os.path.join(backup_folder, IMAGES, head_directory)
    staging_area = os.path.join(backup_folder, STAGING_AREA)
    report = dirscomparison.deep_comparison(
        last_image, staging_area)[1]
    return report['diffrent_files']


def Changes_not_staged_for_commit(backup_folder: str, untracked: bool = False) -> List[str]:
    """Returns all files are in both stageing area and source path but has changed."""
    staging_area = os.path.join(backup_folder, STAGING_AREA)
    source_path = os.path.dirname(backup_folder)
    report = dirscomparison.deep_comparison(
        source_path, staging_area)[1]
    if not untracked:
        return [file for file in report['diffrent_files'] if os.path.isabs(file)]
    return [file for file in report['diffrent_files'] if not os.path.isabs(file)]


@run_only_if_backup
def status(*args: str, **kargs: str) -> None:
    """Prints out the file status."""
    backup_folder = kargs['backup_folder']
    head_directory = get_head(backup_folder)
    print("commit id:\n\t ->".title(), head_directory)

    print("Changes to be committed:".title())
    if not get_head(backup_folder) == 'None':
        print_list(*Changes_to_be_committed(head_directory, backup_folder))
    else:
        print("\t-> None")

    print("Changes not staged for commit:".title())
    print_list(*Changes_not_staged_for_commit(backup_folder))
    print("Untracked files:".title())
    print_list(*Changes_not_staged_for_commit(backup_folder, untracked=True))
    return None


def get_all_branches(path: str) -> Optional[List[Dict[str, str]]]:
    """Return all branches."""
    with open(os.path.join(path, WIT_METADATA_FILE), 'r') as file:
        lines = [line.partition('=') for line in file.readlines()[1:]]
    if not lines:
        return None
    return [{'name': line[0], 'commit_id': line[2].strip()} for line in lines]


def is_branch(path: str, name: str) -> Optional[str]:
    """Return branch commit id is brunch name if is exist."""
    branches = get_all_branches(path)
    if branches:
        for brunch in branches:
            if brunch['name'] == name:
                return brunch['commit_id']
    return None


def set_active_branch(path: str, name: str) -> None:
    """Set name of active branch."""
    with open(os.path.join(path, ACTIVATE_BRANCH), 'w') as file:
        file.write(name)
    return None


def get_active_branch(path: str) -> str:
    """Return the active brance."""
    with open(os.path.join(path, ACTIVATE_BRANCH), 'r') as file:
        return file.read().strip()


@ run_only_if_backup
def checkout(*args: str, **kargs: str) -> None:
    backup_folder = kargs['backup_folder']
    try:
        commit_id = args[0]
    except IndexError:
        print("You need to insert a commit as argument such: 'python x.py checkout COMMIT")
        return None

    branch = is_branch(backup_folder, commit_id)
    if branch is not None:
        commit_id = branch
    else:
        set_active_branch(backup_folder, 'None')

    head_directory = get_head(backup_folder)
    master = get_master(backup_folder)
    # Checks if Commit id path is exist
    if commit_id == 'master':
        head_directory = master
    elif not is_commit_id_valid(backup_folder, commit_id):
        return None

    # Checks id there are not "changes to be commit" or "Changes not staged for commit" files.
    ctbc = Changes_to_be_committed(head_directory, backup_folder)
    cnsfc = Changes_not_staged_for_commit(backup_folder)

    if ctbc or cnsfc:
        return None

    copy_from = os.path.join(backup_folder, IMAGES, commit_id)
    copy_to = os.path.dirname(backup_folder)
    copy_files(copy_from, copy_to, inside=True)

    # Update head to the new commit id.
    update_backup_folder_metadata(backup_folder, commit_id, checkout=True)

    # Deleting the content of a directory
    staging_path = os.path.join(backup_folder, STAGING_AREA)
    delete_dir(staging_path, parent=False)
    copy_files(copy_from, staging_path, inside=True)
    return None


@ run_only_if_backup
def graph(*args: str, **kargs: str) -> None:
    """Display a commit id chain path as a graph."""
    path = kargs['backup_folder']
    g = Digraph('file chain')

    # g.attr(dir="forward", arrowhead='normal', arrowtail='dot')

    all_dirs = dirscomparison.differentiate(os.path.join(path, IMAGES))['dirs']
    all_dirs = {commit: index for index, commit in enumerate(all_dirs, 0)}
    connections = []
    for d in all_dirs:
        g.node(str(all_dirs[d]), f"{d[:20]}\n{d[20:]}")
        parents = get_commit_info(path, d)['parent'].split(',')
        for p in parents:
            if p != 'None' and p:
                connections.append(f"{all_dirs[d]}{all_dirs[p]}")

    g.edges(connections)
    g.render('graph.png', view=True, format='png')
    return None


@ run_only_if_backup
def branch(*args: str, **kargs: str) -> None:
    path = kargs['backup_folder']
    try:
        branch_name = args[0]
    except IndexError:
        print("You need to insert a branch name as argument such: 'python x.py branch NAME")
    else:
        if is_branch(path, branch_name) is None:
            add_branch(path, branch_name)
        else:
            print("Branch name is already exist.")
    return None


def add_branch(path: str, name: str) -> None:
    """Adding branch to reference file."""
    head: str = get_head(path)
    with open(os.path.join(path, WIT_METADATA_FILE), 'a') as file:
        file.write(f"\n{name}={head}")
    return None


@ run_only_if_backup
def merge(*args: str, **kargs: str) -> None:
    path = kargs['backup_folder']
    head = get_head(path)
    staging_area = os.path.join(path, STAGING_AREA)
    try:
        branch_name = args[0]
    except IndexError:
        print("You need to insert a branch name as argument such: 'python x.py merge NAME")

    branch = is_branch(path, branch_name)
    if branch is None:
        print("Your branch name is not exist.")
        return None
    common_branch = get_common_branch(path, branch, head)
    branch_path = os.path.join(path, IMAGES, branch)
    common_branch_path = os.path.join(path, IMAGES, common_branch)

    comperison = dirscomparison.dirs_comparison(
        branch_path, common_branch_path)
    all_diffrents = comperison['diffrent_dirs'].union(
        comperison['diffrent_files'])

    for file in all_diffrents:
        file_optional_path = os.path.join(branch_path, file)
        if os.path.exists(file_optional_path):
            copy_files(file_optional_path, staging_area)

    commit(staging_area,
           f"Branch: {branch} -> merge with {head}", path=path, merge=branch)


def get_all_parents(path: str, commit: str) -> Optional[str]:
    """Parents generator. returns all parents of a commit chain."""
    yield commit
    parents = get_commit_info(path, commit)['parent'].split(',')
    for parent in parents:
        if parent != 'None' and parent:
            yield parent
            yield from get_all_parents(path, parent)


def get_common_branch(path: str, b1: str, b2: str) -> str:
    """Return a common branch name for two given branches."""
    b1_parents = get_all_parents(path, b1)
    b2_parents = get_all_parents(path, b2)
    common_branches = list(set(b1_parents).intersection(set(b2_parents)))
    first = common_branches.pop(0)
    for branch in common_branches:
        first_time = datetime.strptime(
            get_commit_info(path, first)['date'], '%c %z')
        branch_time = datetime.strptime(
            get_commit_info(path, branch)['date'], '%c %z')
        if branch_time > first_time:
            first = branch
    return first


def inputs_manager(f: str, *args: str, **kargs: str) -> None:
    """Manage user inputs and router them to the right function.

    Args:
        f (function): Function name.
        args (tuple): Function arguments.
        kargs (dict): Path of current working directory.
    Returns:
        None.
    """
    functions = {
        'init': init,
        'add': add,
        'commit': commit,
        'status': status,
        'checkout': checkout,
        'graph': graph,
        'branch': branch,
        'merge': merge,
    }
    if f in functions:
        functions[f](*args, **kargs)
    return None


if __name__ == '__main__':
    inputs: List[str] = sys.argv
    path: str = os.getcwd()
    if len(inputs) > 1:
        inputs_manager(inputs[1], *inputs[2:], path=path)
