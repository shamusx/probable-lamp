from avi.sdk.avi_api import ApiSession
import argparse, re
from requests.packages import urllib3
from avi.migrationtools.ansible.avi_config_to_ansible import \
    AviAnsibleConverter

urllib3.disable_warnings()

def refCleanUp(obj):
    ''' Loops through list of policies and datascripts and removes un-needed fields '''
    SKIP_FIELDS = ['uuid', 'url', 'ref_key', 'se_uuids', 'key_passphrase',
                   'extension', '_last_modified']
    if isinstance(obj, dict):
        for cleanObj in SKIP_FIELDS:
            obj.pop(cleanObj, None)
        return {k: refCleanUp(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [refCleanUp(elem) for elem in obj]
    else:
        if isinstance(obj, str):
            return(objectUpdate(obj))
        else:
            return(obj)

def objectUpdate(obj):
    ''' Removes Object IP/UUID from API call and formats it properly for playbooks \n
    Example: \n
    Before: https://10.206.42.183/api/pool/pool-06355c47-5e67-443f-92cf-06e946c95d91#foo_pool \n
    After: /api/pool/?name=foo_pool '''
    matchApi = re.match(".*(/api/\w+).*#(.*)", obj)
    if matchApi:
        return(matchApi.group(1)+'/?name=' + matchApi.group(2))
    else:
        return(obj)

if __name__ == '__main__':
    avi_configuration = {}
    parser = argparse.ArgumentParser()
    parser.add_argument('--controller', required=True, help="Avi Controller IP/Hostname")
    parser.add_argument('--username', required=True, help="Username")
    parser.add_argument('--password', required=True, help="Password")
    parser.add_argument('--tenant', default="admin", help="tenant name")
    parser.add_argument('--name', required=True, help='Name of Object')
    parser.add_argument('--type', required=True, help="Object Type")
    parser.add_argument('--ansible', action='store_true', help="ansible")
    args = parser.parse_args()

    api = ApiSession.get_session(args.controller, args.username, args.password,
                                 tenant=args.tenant)

    resp = api.get_object_by_name(path=args.type.lower(),name=args.name,tenant=args.tenant,params={'include_name':'true'})

    modified_resp = refCleanUp(resp)
    avi_configuration[args.type] = [modified_resp]
    print(avi_configuration)
    if args.ansible:
        gen_playbook = AviAnsibleConverter(avi_configuration, "./", 'test', False,controller_version='21.1.3')
        gen_playbook.write_ansible_playbook()
