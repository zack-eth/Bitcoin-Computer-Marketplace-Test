import json
import yaml
import os.path
import logging
from flask import Flask
from flask import request
from two1.lib.wallet import Wallet
from two1.lib.bitserv.flask import Payment
import Algorithmia

app = Flask(__name__)
wallet = Wallet()
payment = Payment(app, wallet)

@app.before_first_request
def setup_logging():
    if not app.debug:
        # In production mode, add log handler to sys.stderr.
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(logging.INFO)

@app.route('/share_count')
@payment.required(3000)
def share_count():
    input = request.args.get('url')
    client = Algorithmia.client('sime0+26XLqxBgma4HJ65+eQHIv1')
    algo = client.algo('web/ShareCounts/0.2.5')
    return str(algo.pipe(input))

def get_manifest_yaml():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_file = os.path.join(this_dir, 'manifest.yaml')
    with open(manifest_file, 'r') as f:
        manifest_yaml = yaml.load(f)
    return manifest_yaml

@app.route('/manifest')
def docs():
    manifest_yaml = get_manifest_yaml()
    return json.dumps(manifest_yaml)

if __name__ == '__main__':
    manifest_yaml = get_manifest_yaml()
    host = manifest_yaml['host']
    port = int(host.split(':')[1])
    app.run(host='0.0.0.0', port=port)
