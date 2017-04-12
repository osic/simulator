Maximize your Hardware with Server Simulator
===========================

Table of Contents
-----------------

* [#Introduction]()
* [#How to use]()
* [#further work]()

Introduction
------------
TODO: How can this help you

 

How to use
----------

	sudo apt-get install python-pip python-yaml
	sudo pip install netaddr


1. install ansible

	sudo apt-get install software-properties-common
	sudo apt-add-repository ppa:ansible/ansible
	sudo apt-get update
	sudo apt-get install ansible

2. clone repo

	git clone https://github.com/raddaoui/simulator.git


3. configure the simulator


Open the `simulator user config file` and configure the subnets of your pxe, management, tunnel, storage and flat networks. Then configure the dhcp pool range where VMs can take IPs, interface used by cobbler to pxeboot VMs, how many Vms you want to create per host, all already used ips by your environment, nodes where you want to create Vms, the disk in each host where your VMs will be mouned. 

	cd simulator
	vi sim_user_config.yml
  
3. generate an inventory for your VMs
	
	python generate_sim_inv.py

4. Bootstrap your hosts 

	cd playbooks
	ansible-playbook -i inventory/static-inventory.yml bootstrap_hosts.yml

5. Install cobbler in your deployment host

	cd ..
	./setup-cobbler.sh (look for templates preseeds)

6. partition disk in each server and mount it to /var/lib/libvirt/

	cd playbooks
	ansible-playbook -i inventory/static-inventory.yml partition_disk.yml  

7. Create virsh bridged networks in your servers to which VMs will be attached

	ansible-playbook -i inventory/static-inventory.yml setup-virsh-net.yml

8. Create VMs
	
	ansible-playbook -i inventory/static-inventory.yml deploy-vms.yml

9. (optional): reckick all VMs to restart with a clean environment
	
	ansible-playbook -i inventory/static-inventory.yml rekick_vms.yml




further work
------------

- test against ubuntu16.04

- VMs specs can be configured

- rebuild specific VM capability

