from avi.sdk.avi_api import ApiSession
import argparse, re
from requests.packages import urllib3
import time
import yaml, json, os

urllib3.disable_warnings()

# SKIPS
SKIP_FIELDS = ['uuid', 'url', 'ref_key', 'se_uuids', 'key_passphrase',
               'extension', '_last_modified']

class AviAnsibleBuilder():
    def __init__(self, config):
        self.auth_args = {
            'controller': "{{ controller }}",
            'username': "{{ username }}",
            'password': "{{ password }}"
        }

        self.ansible_dict = dict({
            'hosts': 'localhost',
            'collections': ['vmware-alb'],
            'vars': self.auth_args,
            'tasks': []})
        self.path = ''
        self.config = config
        self._build_task()

    def _build_task(self):
        for l in self.config:
            for k,v in l.items():
                for config in v:
                    config.update(self.auth_args)
                    self.ansible_dict['tasks'].append({'avi_'+k:config})

class AviConfig(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.runtime = int(time.time())
        self.folder = './'+self.folder

        avi_configuration = self.collectConfig()

        self.createDir(self.folder)
        self.createFile(json.dumps(avi_configuration),self.name+'-'+str(self.runtime)+'.json')

        if self.ansible:
            ansible_configuration = AviAnsibleBuilder(avi_configuration)
            self.createDir(self.folder+'/ansible'+self.name + '-' + str(self.runtime))
            self.createFile(yaml.dump(ansible_configuration.ansible_dict),'ansible'+self.name + '-' + str(self.runtime)+'/main.yml')

    def createDir(self, dirname):
        if not os.path.exists(dirname):
            os.mkdir(dirname)

    def createFile(self, content, filename):
        with open(self.folder+'/'+filename, 'w') as f:
            f.write(content)

    def refCleanUp(self, obj):
        ''' Loops through list of policies and datascripts and removes un-needed fields '''
        if isinstance(obj, dict):
            for cleanObj in SKIP_FIELDS:
                obj.pop(cleanObj, None)
            return {k: self.refCleanUp(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.refCleanUp(elem) for elem in obj]
        else:
            if isinstance(obj, str):
                return(self.objectUpdate(obj))
            else:
                return(obj)
    
    def objectUpdate(self,obj):
        ''' Removes Object IP/UUID from API call and formats it properly for playbooks \n
        Example: \n
        Before: https://10.206.42.183/api/pool/pool-06355c47-5e67-443f-92cf-06e946c95d91#foo_pool \n
        After: /api/pool/?name=foo_pool '''
        matchApi = re.match(".*(/api/\w+).*#(.*)", obj)
        if matchApi:
            return(matchApi.group(1)+'/?name=' + matchApi.group(2))
        else:
            return(obj)
    
    def collectConfig(self):
        avi_configuration = []
        api = ApiSession.get_session(self.controller, self.username, self.password,
                                     tenant=args.tenant)
        resp = api.get_object_by_name(path=self.type.lower(), name=self.name, tenant=self.tenant,
                                      params={'include_name': 'true'})
        avi_configuration.append({args.type.lower(): [self.refCleanUp(resp)]})
        return(avi_configuration)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--controller', required=True, help="Avi Controller IP/Hostname")
    parser.add_argument('--username', required=True, help="Username")
    parser.add_argument('--password', required=True, help="Password")
    parser.add_argument('--tenant', default="admin", help="tenant name")
    parser.add_argument('--name', required=True, help='Name of Object')
    parser.add_argument('--type', required=True, help="Object Type")
    parser.add_argument('--ansible', action='store_true', help="ansible")
    parser.add_argument('--folder', default='output', help="folder to store outputs from script")
    args = parser.parse_args()

    AviConfig(**args.__dict__)