# ddueruem
A wrapper for the BDD library BuDDy (CUDD, Sylvan, CacBDD to follow)

### Usage:
```bash
# create virtual environment (Python 3.x)
python -m venv .venv

# activate venv
source .venv/bin/activate

# install required packages
pip install -r requirements.txt

# show ddueruem help
./ddueruem -h

# install BuDDy
./ddueruem --install-buddy

# create BDD for example sandwich.dimacs
./ddueruem examples/sandwich.dimacs
```

### Troubleshooting
1) `bash: ./ddueruem.py: Permission denied` <br>
**Solution:** Execute `chmod u+x ddueruem.py` to make the file executable.