#! /bin/env python

import json
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.playbook import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.executor.task_result import TaskResult

import pprint
import json
import requests
import sys
import time
import os

playbook_store_path = '/opt/ansiblefactory/playbooks/'
logdir='/opt/ansiblefactory/logs/'


def get_output(tasks_results,hostname):
    results = []
    for taskd in tasks_results:
        task_name = taskd["task"]["name"] if taskd["task"]["name"] else '_unnamed_task'
        host_data = taskd["hosts"][hostname] 
        task_filtered_data = {}
        task_filtered_data['name'] = task_name
        task_filtered_data['host'] = hostname
        fields = ['rc','stderr','stdout']
        for f in fields:
            if f in host_data:
                task_filtered_data[f] = host_data[f]
        results.append(task_filtered_data)
    return results

def log_results(results, hostname):
    curdate_infile = time.strftime("%d/%m/%Y %H:%M:%S")
    curdate_infilename = time.strftime("%Y%d%m_%H-%M-%S")
    with open(os.path.join(logdir, '%s_ansiblelog_%s' %(curdate_infilename, hostname)), 'w+') as logfile:
        for taskret in results:
            name = taskret['name'] if 'name' in taskret else '_no_name'
            rc = taskret['rc'] if 'rc' in taskret else '_no_rc'
            stderr = taskret['stderr'] if 'stderr' in taskret else '_no_stderr'
            stdout = taskret['stdout'] if 'stdout' in taskret else '_no_stdout'
            logfile.write('####   task: %s, return_code: %s    ####\n' % (name, rc))
            logfile.write('stdout:\n')
            logfile.write(stdout+'\n')
            logfile.write('stderr:\n')
            logfile.write(stderr+'\n')
    return os.path.join(logdir, '%s_ansiblelog_%s' %(curdate_infilename, hostname))        


def execute_playbook(playbook, host, *args, **kwargs):
    playbook = os.path.join(playbook_store_path,playbook)
    Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check', 'remote_user', 'listhosts', 'listtasks', 'listtags', 'syntax', 'verbose'])

    #needed objects
    variable_manager = VariableManager()
    loader = DataLoader()
    options = Options(connection='ssh', module_path='./modules', forks=100, become=None, become_method=None, become_user=None, check=False, remote_user='root', listhosts=None, listtasks=None, listtags=None, syntax=None, verbose=None)
    passwords = dict(vault_pass='secret')


    #Create inventory and pass to manager
    inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=[host])
    variable_manager.set_inventory(inventory)
    hostobj = inventory.get_host(host)
    for varname, value in kwargs.iteritems():
        variable_manager.set_host_variable(hostobj, varname, value)


    #Should execute fine
    executor = PlaybookExecutor(playbooks=[ playbook ], inventory=inventory,
            variable_manager=variable_manager, loader=loader, options=options,
            passwords=passwords)

    #Forcing our callback object into the executor
    executor._tqm._stdout_callback = "json" 

    results = executor.run()
    pprint.pprint(results)
    report_tasks = executor._tqm._stdout_callback.results[0]['tasks']
    report = executor._tqm._stdout_callback.results
    report_stats = executor._tqm._stats.summarize(host)
    results_output = get_output(report_tasks, host)
    return dict(stats = report_stats, results = results_output)


if __name__ == '__main__':
    host = 'dock001'
    exec_results = execute_playbook('test/site.yml', host)
    logfile_path = log_results(exec_results['results'], host)
    if exec_results['stats']['failures'] > 0 or exec_results['stats']['unreachable'] > 0:
        print('Errors')
    else:
        print('Success')
    pprint.pprint(exec_results['stats'])

    print('Sending logfile')
    logfile_results = execute_playbook('ansiblefactory/uploadlogs.yml', host, logfile=logfile_path)
    pprint.pprint(logfile_results['stats'])

