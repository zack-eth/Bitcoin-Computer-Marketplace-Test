import pytest
from two1.tests import test_utils
from two1.lib.util import zerotier
import yaml
import os
import re
import time
from os import path
from subprocess import check_call
from subprocess import getoutput
from subprocess import Popen
from subprocess import PIPE
from random import randint

this_dir = path.dirname(path.abspath(__file__))
app_dir = path.join(this_dir, 'share_counts')
setup_script = path.join(app_dir, 'setup.sh')
check_call(['bash', setup_script])

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from marketplace_page_object import MarketplacePageObject
from marketplace_page_object import MARKETPLACE_URL

class MarketIntegrationTest(object):

    def __init__(self, cli_runner):
        self.cli_runner = cli_runner
        self.server_script = path.join(app_dir, 'index.py')
        self.path_to_manifest = path.join(app_dir, 'manifest.yaml')
        self.read_manifest()
        self.app_name = self.manifest_yaml['info']['title']
        self.set_host(6000)
        self.set_account()
        self.set_name(self.account)

    def read_manifest(self):
        with open(self.path_to_manifest, 'r') as f:
            self.manifest_yaml = yaml.load(f)

    def write_manifest(self):
        with open(self.path_to_manifest, 'w') as f:
            f.write(yaml.dump(self.manifest_yaml))

    def set_host(self, port):
        ip_address = zerotier.device_ip('6c0c6960a20bf150')[0]
        port = str(port)
        self.host = ':'.join([ip_address, port])
        self.server_url = "http://{}/share_count?url=".format(self.host)
        self.manifest_yaml['host'] = self.host
        self.manifest_yaml['info']['x-21-quick-buy'] = "21 buy url http://{}/share_count?url=URL_TO_COUNT".format(self.host)
        self.write_manifest()
        print("Using host {}".format(self.host))

    def set_account(self):
        status = self.cli_runner.get_status()
        self.account = status['account']['username']
        print("Using 21 account {}".format(self.account))

    def set_name(self, name):
        self.name = name
        self.manifest_yaml['info']['contact']['name'] = self.name
        self.write_manifest()
        print("Using contact name {}".format(self.name))

    def start_server(self):
        self.kill_server()
        print('Starting server and keeping it up ...')
        # replace with `21 sell` when that command is ready
        server = Popen(['python3', self.server_script], stderr=PIPE)
        while True:
            line = server.stderr.readline().decode('utf-8')
            if 'Running on http://0.0.0.0:' in line:
                server.stderr.close()
                break
            else:
                time.sleep(1)

    def kill_server(self):
        ps_grep = 'ps ax | grep {} | grep -v grep'.format(self.server_script)
        if getoutput(ps_grep) != '':
            print('Killing server ...')
            check_call(['sudo', 'pkill', '-f', self.server_script])

    def delete(self):
        publish_list = self.cli_runner.publish_list()
        try:
            published_entries = re.findall("\|(.*)\|\s{}".format(self.app_name), publish_list)
            for published_entry in published_entries:
                id = published_entry.strip()
                print("Removing instance {} of app {} ...".format(id, self.app_name))
                self.cli_runner.publish_remove(id)
        except:
            print("{} does not have any apps published to the marketplace yet".format(self.account))

    def publish(self):
        print('Publishing app to marketplace ...')
        result = self.cli_runner.publish_submit(self.path_to_manifest)
        if 'has already been registered in the marketplace' in result:
            print("Endpoint {} taken".format(self.manifest_yaml['host']))
            port = randint(5000,65535)
            self.set_host(port)
            self.start_server()
            self.publish()
        time.sleep(60*2) # wait a couple of minutes for app to show up in the marketplace

    def search_found_cli(self):
        print('Searching for app using cli ...')
        timeout = time.time() + 60*5
        while True:
            if time.time() > timeout:
                print('Unable to find app in marketplace')
                return False
            search_results = self.cli_runner.search(self.account)
            if 'Details' in search_results:
                if self.app_name in search_results:
                    return True

    def search_not_found_cli(self):
        print('Searching for app using cli ...')
        timeout = time.time() + 60*5
        while True:
            if time.time() > timeout:
                print('App still found in marketplace')
                return False
            search_results = self.cli_runner.search(self.account)
            if 'Details' in search_results:
                if self.app_name not in search_results:
                    return True
            elif "couldn't find" in search_results:
                return True

    def search_found_web(self):
        print("Searching for app {} by {} on {} ...".format(self.app_name, self.name, MARKETPLACE_URL))
        timeout = time.time() + 60*5
        found = False
        while found is False:
            if time.time() > timeout:
                print('Unable to find app in marketplace')
                return False
            with MarketplacePageObject() as marketplace:
                found = marketplace.find(self.app_name, self.name)
        return found

    def search_not_found_web(self):
        print("Searching for app {} by {} on {} ...".format(self.app_name, self.name, MARKETPLACE_URL))
        timeout = time.time() + 60*5
        not_found = False
        while not_found is False:
            if time.time() > timeout:
                print('App still found in marketplace')
                return False
            with MarketplacePageObject() as marketplace:
                not_found = not marketplace.find(self.app_name, self.name)
        return not_found

    def reset(self):
        name = '<<name_or_pseudonym>>'
        self.set_name(name)
        print("Resetting name to {} ...".format(name))
        assert self.name == name

    def update(self):
        self.set_name(self.account)
        print("Updated name to {}".format(self.name))
        assert self.name != '<<name_or_pseudonym>>'

    def buy(self):
        self.buy_on_chain()
        self.buy_off_chain()
        # self.buy_through_channel()

    def buy_on_chain(self):
        print('Buying url using onchain balance ...')
        output = self.cli_runner.buy_url(self.server_url + 'https://21.co/learn/', 'onchain')
        print(output)
        assert 'You spent:' in output
        assert 'Remaining blockchain balance:' in output

    def buy_off_chain(self):
        print('Buying url using offchain balance ...')
        output = self.cli_runner.buy_url(self.server_url + 'https://21.co/buy/', 'offchain')
        print(output)
        assert 'You spent:' in output
        assert 'Remaining 21.co balance:' in output

    def buy_through_channel(self):
        print('Buying url using payment channel ...')
        output = self.cli_runner.buy_url(self.server_url + 'https://21.co/buy/', 'channel')
        print(output)
        assert 'You spent:' in output
        assert 'Remaining payment channels balance:' in output

    def run_test(self):
        self.start_server()

        self.publish()
        assert self.search_found_cli()
        assert self.search_found_web()

        self.delete()
        assert self.search_not_found_cli()
        assert self.search_not_found_web()

        self.reset()
        self.publish()
        assert self.search_found_cli()
        assert self.search_found_web()

        self.update()
        self.publish()
        assert self.search_found_cli()
        assert self.search_found_web()

        self.buy()

        self.delete()

@test_utils.integration
def test_market(cli_runner, **kwargs):
    test = MarketIntegrationTest(cli_runner)
    test.run_test()
