import xml.etree
import xml.etree.ElementTree
import svn
import svn.common
import svn.remote
import svn.local

import argparse
import xml
import json
import os

# todo init svn client with my username and password then compare local specific dir with remote
def get_svn_client(svn_url, username, password):
    try:
        return svn.remote.RemoteClient(svn_url, username=username, password=password)
    except svn.common.SVNException as e:
        print(f"Error connecting to SVN repository: {e}")
        return None
    
    
def get_svn_client_local(svn_path):
    try:
        return svn.local.LocalClient(svn_path)
    except svn.common.SVNException as e:
        print(f"Error connecting to local SVN repository: {e}")
        return None


def licensePath():
    user_dir = os.path.expanduser('~')
    license_path = os.path.join(user_dir, 'license.json')
    return license_path

def getLicenseFile() -> list:
    license_path = licensePath()
    if not os.path.exists(license_path):
        print('license.json not found, return []')
        return []
    
    str = None
    with open(license_path, 'r') as license_file:
        str = license_file.read()
    if str == '':
        return []
    license_list = json.loads(str)
    return license_list
    

def setLicenseFile(license_list : list):
    license_path = licensePath()
    if not os.path.exists(license_path):
        print('create license.json')
    
    with open(license_path, 'w') as license_file:
        json_str = json.dumps(license_list, indent=4)
        license_file.write(json_str)
    

def isFile(path):
    dot_idx = path.rfind('.')
    if dot_idx > path.rfind('\\'): 
        return True
    else:
        return False

def getFileType(path : str):
    return path[path.rfind(".") + 1 :]

def getUnversioned(client):
    arguments = ['{0}'.format(local_path), '--xml']
    # arguments = ['{0}'.format(local_path)]
    result = client.run_command('status', arguments, do_combine=True)
    root = xml.etree.ElementTree.fromstring(result)
    diff = []
    
    for element in root.findall('target/entry'):
        if element.find('wc-status').attrib['item'] != 'unversioned':
            continue
        diff.append({
            'path': element.attrib['path']
            })
    
    return diff
    

def getVersioned(client):
    arguments = [
        '--old', '{0}@{1}'.format(remote_path, 'HEAD'),
        '--new', '{0}'.format(local_path),
        '--summarize',
        '--xml',
    ]
    result = client.run_command('diff', arguments, do_combine=True)
    
    root = xml.etree.ElementTree.fromstring(result)

    diff = []
    for element in root.findall('paths/path'):
        if element.attrib['kind'] != 'file':
            continue
        diff.append({
            'path': element.text,
            'item': element.attrib['item'],
            })
    return diff

def compareLocalWithRemote(svn_url, local_path, username, password):
    client = get_svn_client(svn_url, username, password)
    diff = [{'path': "unversioned"}]
    diff = diff + getUnversioned(client)
    diff = diff + [{'path': "versioned"}]
    diff = diff + getVersioned(client)

    return diff

def certificate(remote_path):
    license_list = getLicenseFile()
    
    for item in license_list:
        if item['remote'] == remote_path:
            return item['user'], item['password']
    print("Can't find the license for " + remote_path)
    print("adding new license at" + licensePath())
    
    user = input("Svn Username:")
    password = input("Svn Password:")
    new_license = {
                'remote' : remote_path,
                'user' : user,
                'password' : password
            }
    
    license.append(new_license) 
    setLicenseFile(new_license)
    return user, password

def setIgnored(remote_path : str, ignored : list):
    license_list = getLicenseFile()
    for item in license_list:
        if item['remote'] == remote_path:
            item['ignored'] = ignored
            setLicenseFile(license_list)
            return

def getIgnored(remote_path : str) -> list:
    license_list = getLicenseFile()
    for item in license_list:
        if item['remote'] == remote_path:
            if 'ignored' in item:
                return item['ignored']
            else:
                return []
    return []


def ignoreFile(path : str, ignored : list):
    for item in ignored:
        if item in path:
            return True
    
    
    return False


def filter_diff(diff, diff_filter : dict):
    paths = []
    
    for item in diff:
        if item['path'] == "unversioned":
            print(" >> unversioned <<")
            continue
        elif item['path'] == "versioned":
            print(" >> versioned <<")
            continue
        
        path : str = item['path']
        # to avoid the different format between remote and local
        path = path.replace('/', '\\')
        path = path[path.find('PowerSys'):]
        if isFile(path) and not ignoreFile(path, diff_filter['ignored']):
            file_path = path
            if diff_filter['subPrj'] is None or file_path.find(diff_filter['subPrj']) != -1:
                if diff_filter['fileType'] is not None:
                    for suffix in diff_filter['fileType']:
                        if getFileType(file_path) == suffix:
                            file_path = '\\' + file_path
                            print(file_path)
                            paths.append(file_path)
                else:
                    file_path = '\\' + file_path
                    print(file_path)
                    paths.append(file_path)

    return paths    


if __name__ == '__main__':
    # add arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', help='path to project')
    parser.add_argument('-i', '--ignore', help='ignored files or dirs, which will be add in license.json', default='null')
    parser.add_argument('-s', '--subPrj', help='sub project name, enter null to get all', default='null')
    parser.add_argument('-t', '--type', help='file type, enter null to get all', default='null')
    args = parser.parse_args()
    subPrj = args.subPrj
    local_path = args.path
    fileType = args.type
    ignored : str = args.ignore

    client = get_svn_client_local(local_path)
    remote_path = client.info()["repository_root"]    
    if ignored != 'null':
        setIgnored(remote_path, ignored.split(','))
    else: 
        if subPrj == 'null':
            subPrj = None
        
        if fileType == 'source':
            fileType = ['.cpp', '.cxx', '.c', '.h', '.hpp']
        elif fileType == 'null':
            fileType = None
        else:
            fileType = [fileType]
                

        user, password = certificate(remote_path)
        
        if compareLocalWithRemote(remote_path, local_path, user, password) is None:
            print("Error: Can't connect to remote repository.")
            exit(1)
        
        diff = compareLocalWithRemote(remote_path, local_path, user, password)
        

        diff_fliter = {
            'subPrj' : subPrj,
            'fileType' : fileType,
            'ignored' : getIgnored(remote_path)
        }
        
        paths = filter_diff(diff, diff_fliter)