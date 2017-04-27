#!/usr/bin/env python

import os
from os import path
import sys
import yaml
import netaddr
import json
import re

LIB_DIR = path.join(os.getcwd(), 'lib')
sys.path.append(LIB_DIR)

import ip

USED_IPS = set()

def set_used_ips(user_defined_config):
    """Set all of the used ips into a global list.
    :param user_defined_config: ``dict`` User defined configuration
    """
    used_ips = user_defined_config.get('used_ips')
    if isinstance(used_ips, list):
        for ip in used_ips:
            split_ip = ip.split(',')
            if len(split_ip) >= 2:
                ip_range = list(
                    netaddr.iter_iprange(
                        split_ip[0],
                        split_ip[-1]
                    )
                )
                USED_IPS.update([str(i) for i in ip_range])
            else:
                logger.debug("IP %s set as used", split_ip[0])
                USED_IPS.add(split_ip[0])


def load_user_configuration(config_path):
    """Create a user configuration dictionary from config files

    :param config_path: ``str`` path where the configuration files are kept
    """

    user_defined_config = dict()

    # Load the user defined configuration file
    if os.path.isfile(config_path):
        with open(config_path, 'rb') as f:
            user_defined_config.update(yaml.safe_load(f.read()) or {})


    # Exit if no user_config was found and loaded
    if not user_defined_config:
        raise SystemExit(
            'No user config loaded\n'
        )
    return user_defined_config



def get_sim_hosts(user_defined_config):
    return user_defined_config.get('simulator_hosts').keys()


def generate_inv(sim_hosts, manager, vms_per_host):
    nodes_index = 1
    inv = {}
    for host in sim_hosts:
      inv[host] = {}
      inv[host]["nova_compute"] ={}
      for i in range(vms_per_host):
        inv[host]["nova_compute"]["simulated" + str(nodes_index) ] = {}
        inv[host]["nova_compute"]["simulated" + str(nodes_index)]["ansible_pxe_host"] = manager.get('pxe')
        inv[host]["nova_compute"]["simulated" + str(nodes_index)]["ansible_mgmt_host"] = manager.get('mgmt')
        inv[host]["nova_compute"]["simulated" + str(nodes_index)]["ansible_tunnel_host"] = manager.get('tunnel')
        inv[host]["nova_compute"]["simulated" + str(nodes_index)]["ansible_storage_host"] = manager.get('storage')
        inv[host]["nova_compute"]["simulated" + str(nodes_index)]["ansible_flat_host"] = manager.get('flat')
        nodes_index = nodes_index + 1
    return inv

def configure_simulator(var_file, var_file_ansible, user_defined_config): 
    # Load the user defined configuration file
    cobbler_interface = user_defined_config.get('cobbler_interface')
    dhcp_range = user_defined_config.get('dhcp_range')
    DEVICE_NAME = user_defined_config.get('DEVICE_NAME')
    DEFAULT_NETWORK = user_defined_config.get('DEFAULT_NETWORK')
    cidr_networks = user_defined_config.get('cidr_networks')
    pxe_cidr = cidr_networks['pxe']['subnet']
    pxe_gateway = cidr_networks['pxe']['gateway']
    use_disk = user_defined_config.get('use_disk')
    with open(var_file, 'r+b') as f:
      text = f.read()
      p = re.compile('cobbler_interface=.*')
      text = p.sub('cobbler_interface=' + cobbler_interface, text)
      p = re.compile('dhcp_range=.*')
      text = p.sub('dhcp_range=' + dhcp_range, text)
      p = re.compile('DEVICE_NAME:-.*')
      text = p.sub('DEVICE_NAME:-' + DEVICE_NAME + '}"' , text)
      p = re.compile('DEFAULT_NETWORK:-.*')
      text = p.sub('DEFAULT_NETWORK:-' + DEFAULT_NETWORK + '}"' , text)
      p = re.compile('pxe_subnet=.*')
      text = p.sub('pxe_subnet=' + str(netaddr.IPNetwork(pxe_cidr).network), text)
      p = re.compile('pxe_gateway=.*')
      text = p.sub('pxe_gateway=' + pxe_gateway, text)
      p = re.compile('pxe_mask=.*')
      text = p.sub('pxe_mask=' + str(netaddr.IPNetwork(pxe_cidr).netmask), text)
      f.seek(0)
      f.truncate()
      f.write(text)
    with open(var_file_ansible, 'r+b') as f:
      text = f.read()
      p = re.compile('use_disk=.*')
      text = p.sub('use_disk=' + use_disk, text)
      f.seek(0)
      f.truncate()
      f.write(text)

def main():
    "main function"

    config_file = "sim_user_config.yml"
    user_defined_config = load_user_configuration(config_file)

    # get hosts that will be used by simulator
    sim_hosts = get_sim_hosts(user_defined_config)
    vms_per_host = int(user_defined_config.get('vms_per_host'))

    # get cidr_networks
    cidr_networks = user_defined_config.get('cidr_networks')
    if not cidr_networks:
        raise SystemExit('No nodes CIDR specified in user config')
    try: 
        pxe_cidr = cidr_networks['pxe']['subnet']
        pxe_gateway = cidr_networks['pxe']['gateway']
        mgmt_cidr = cidr_networks['mgmt']['subnet']
        tunnel_cidr = cidr_networks['tunnel']['subnet']
        storage_cidr = cidr_networks['storage']['subnet']
        flat_cidr = cidr_networks['flat']['subnet']
    except Exception as e:
        raise SystemExit('one of pxe, mgmt, tunnel, flat or storage network is not'
                         'specified in user config.')

    var_file = "vars.rc"
    var_file_ansible = "playbooks/vars/main.yml"
    configure_simulator(var_file, var_file_ansible, user_defined_config)
    # Load all of the IP addresses that we know are used
    set_used_ips(user_defined_config)
    # exclude broadcast and network ips for each cidr
    base_exclude = []
    for cidr in [pxe_cidr, mgmt_cidr, tunnel_cidr, storage_cidr, flat_cidr]:
        base_exclude.append(str(netaddr.IPNetwork(cidr).network))
        base_exclude.append(str(netaddr.IPNetwork(cidr).broadcast))
    USED_IPS.update(base_exclude)

    # set the queues
    manager = ip.IPManager(queues={'pxe': pxe_cidr, 'mgmt': mgmt_cidr, 'tunnel': tunnel_cidr, 'storage': storage_cidr, 'flat': flat_cidr},
                             used_ips=USED_IPS)
    # generate inventory
    inv = generate_inv(sim_hosts, manager, vms_per_host)
    # save inventory
    with open('sim_inv.json', 'w') as outfile:
      json.dump(inv, outfile)
    # generate osa inventory
    with open('compute_vms.yml', 'w') as f:
      f.write('---\n')
      f.write('compute_vms:\n')
      for (k,v) in inv.items():
        for(kk,vv) in v.items():
          for (kkk,vvv) in vv.items():
            f.write('  ' + kkk + ':\n')
            f.write('    ip: ' + vvv['ansible_mgmt_host'] + '\n')
      f.close()
    # generate static inventory
    with open('compute_vms_static_inv.yml', 'w') as f:
      f.write('[compute_vms]\n')
      for (k,v) in inv.items():
        for(kk,vv) in v.items():
          for (kkk,vvv) in vv.items():
            f.write(kkk + '  ansible_ssh_host=' + vvv['ansible_pxe_host'] + '\n')
      f.close()

if __name__ == "__main__":

    main()
