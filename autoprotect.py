import argparse
import datetime
import json
import logging
import sys

from subprocess import check_output, call


# create logger with 'autoprotect'
logger = logging.getLogger('autoprotect')
logger.setLevel(logging.DEBUG)


def parse_rc_file(rcfile):
    params = {}
    _mapping = {'--os-auth-url': 'OS_AUTH_URL',
               '--os-project-id': 'OS_PROJECT_ID',
               '--os-tenant-id': 'OS_TENANT_ID',
               '--os-project-name': 'OS_PROJECT_NAME',
               '--os-user-domain-name': 'OS_USER_DOMAIN_NAME',
               '--os-project-domain-name': 'OS_PROJECT_DOMAIN_NAME',
               '--os-project-domain-id': 'OS_PROJECT_DOMAIN_ID',
               '--os-username': 'OS_USERNAME',
               '--os-region-name': 'OS_REGION_NAME',
               '--os-interface': 'OS_INTERFACE',
               '--os-identity-api-version': 'OS_IDENTITY_API_VERSION',
               '--os-password': 'OS_PASSWORD',
               '--os-domain-id': 'OS_DOMAIN_ID',
               '--os-backup-admin-password': 'OS_BACKUP_ADMIN_PASSWORD',
               '--os-backup-admin': 'OS_BACKUP_ADMIN',
               'job-interval': 'JOB_INTERVAL',
               'snaps-to-retain': 'SNAPS_TO_RETAIN',
               'start-date': 'START_DATE',
               'start-time': 'START_TIME',
               'log_file': 'log_file',
               'vm_age': 'vm_age'} 
   
    mapping = {}
    for k, v in _mapping.items():
        mapping[v] = k
               
    for line in rcfile:
        if len(line.strip().split()) < 2:
            continue
        exp = line.strip().split()[0]
        if exp == 'export':
            var = line.strip().split()[1].strip().split("=")[0].strip()
            value = line.strip().split()[1].strip().split("=")[1].strip().strip('"').strip("'")
            params[mapping[var]] = value
    return params


def list_domains(params):
    cmd = "/bin/openstack --os-interface %s --os-password %s --os-identity-api-version %s --os-domain-id %s --os-project-id %s --os-auth-url %s --os-username %s --os-region-name %s domain list -f json" % \
          (params["--os-interface"], params["--os-password"],
           params["--os-identity-api-version"],
           params["--os-domain-id"], params["--os-project-id"],
           params["--os-auth-url"], params["--os-username"],
           params["--os-region-name"])

    out = check_output(cmd.split())
    return json.loads(out)


def list_projects(params, domain):
    cmd = "/bin/openstack --os-interface %s --os-password %s --os-identity-api-version %s --os-domain-id %s --os-project-id %s --os-auth-url %s --os-username %s --os-region-name %s project list --domain %s -f json" % \
          (params["--os-interface"], params["--os-password"],
           params["--os-identity-api-version"],
           params["--os-domain-id"], params["--os-project-id"],
           params["--os-auth-url"], params["--os-username"],
           params["--os-region-name"], domain)

    out = check_output(cmd.split())
    return json.loads(out)


def list_users(params, domain):
    cmd = "/bin/openstack --os-interface %s --os-password %s --os-identity-api-version %s --os-domain-id %s --os-project-id %s --os-auth-url %s --os-username %s --os-region-name %s user list --domain %s -f json" % \
          (params["--os-interface"], params["--os-password"],
           params["--os-identity-api-version"],
           params["--os-domain-id"], params["--os-project-id"],
           params["--os-auth-url"], params["--os-username"],
           params["--os-region-name"], domain)

    out = check_output(cmd.split())
    return json.loads(out)


def list_instances(params, project):
    cmd = "/bin/openstack --os-interface %s --os-password %s --os-identity-api-version %s --os-domain-id %s --os-project-id %s --os-auth-url %s --os-username %s --os-region-name %s server list --project %s -f json" % \
          (params["--os-interface"], params["--os-password"],
           params["--os-identity-api-version"],
           params["--os-domain-id"], params["--os-project-id"],
           params["--os-auth-url"], params["--os-username"],
           params["--os-region-name"], project)

    out = check_output(cmd.split())
    return json.loads(out)


def show_instance(params, vmid):
    cmd = "/bin/openstack --os-interface %s --os-password %s --os-identity-api-version %s --os-domain-id %s --os-project-id %s --os-auth-url %s --os-username %s --os-region-name %s server show %s -f json" % \
          (params["--os-interface"], params["--os-password"],
           params["--os-identity-api-version"],
           params["--os-domain-id"], params["--os-project-id"],
           params["--os-auth-url"], params["--os-username"],
           params["--os-region-name"], vmid)

    out = check_output(cmd.split())
    return json.loads(out)

def create_workload(params, domainid, projectid, backupadmin, backupadmin_password, vm):
    date = datetime.datetime.now() + datetime.timedelta(days=int(params['start-date']))
    start_date = date.strftime("%x")
    start_time = datetime.datetime.strptime(params['start-time'], "%X").strftime("%I:%M %p")
    cmd = "workloadmgr --endpoint-type %s  --os-auth-url %s --os-domain-id %s --os-tenant-id %s "                  \
          "--os-username %s --os-password %s workload-create --display-name workload-%s "                          \
          "--display-description %s --instance instance-id=%s --jobschedule interval=%s "                          \
          "--jobschedule retention_policy_value=%s --jobschedule start_date=%s "                                   \
          "--jobschedule enabled=True" % \
          (params["--os-interface"], params["--os-auth-url"], domainid, projectid,
           backupadmin, backupadmin_password, vm['name'], "created-by-autoprotect-script",
           vm['id'], params["job-interval"], params["snaps-to-retain"], start_date)

    out = check_output(cmd.split() + ["--jobschedule", "start_time='%s'" % start_time])
    logger.info("Creating workload for VM %s(%s)" % ( vm['name'], vm['id']))
    logger.info(out)
    return out


if __name__ == '__main__':
   # create file handler which logs even debug messages
   parser = argparse.ArgumentParser()
   parser.add_argument('rcfile', type=argparse.FileType('r'))
   args = parser.parse_args()
   params = parse_rc_file(args.rcfile)

   log_file = params.get('log_file', 'autoprotect.py.log')
   fh = logging.FileHandler(log_file)
   fh.setLevel(logging.DEBUG)

   # create formatter and add it to the handlers
   formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
   fh.setFormatter(formatter)

   # add the handlers to the logger
   logger.addHandler(fh)
   logger.info("============================= Start of autoprotect.py script =====================")

   domains = list_domains(params)
   vm_age = int( params.get('vm_age', 0))
   for d in domains:
       backup_admin_id = None
       users = list_users(params, d['ID'])
       for u in users:
           if u['Name'] == params['--os-backup-admin']:
               backup_admin_id = u['ID']
               break
       if not backup_admin_id:
           continue
       for p in list_projects(params, d['ID']):
           for i in list_instances(params, p['ID']):
               vm = show_instance(params, i['ID'])
               if datetime.datetime.now() - datetime.datetime.strptime(vm['created'], "%Y-%m-%dT%XZ") < datetime.timedelta(days=vm_age):
                   logger.info("Skipping VM(%s) as it is created less than %d days" % (vm['name'], vm_age))
                   continue
               if 'workload_id' in vm.get('properties'):
                   logger.info("VM(%s) is protected" % vm['name'])
               else:
                   logger.info("VM(%s) is NOT protected" % vm['name'])
                   logger.info(create_workload(params, d['ID'], p['ID'],
                                         params["--os-backup-admin"],
                                         params["--os-backup-admin-password"], vm))
   logger.info("============================= End of autoprotect.py script =====================")
