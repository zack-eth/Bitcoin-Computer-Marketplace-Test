channels sync

DIR=`dirname $0`
pip3 install -r "$DIR/requirements.txt"

ALGORITHMIA_PATH=`python3 -c "import sys; from os import path; import site; dir = [p for p in sys.path if p.endswith('site-packages')][-1] if hasattr(sys,'real_prefix') else site.getsitepackages()[0]; print(path.join(dir, 'Algorithmia'))"`
2to3 -w $ALGORITHMIA_PATH > /dev/null 2>&1
