# DocFub
🔌 Access [UrLab's DocHub](https://github.com/urlab/dochub) over FUSE 📡


## Usage

At the moment this is only usable by people who have a syslogin (only developers)

### Install

```bash
git clone https://github.com/titouanc/docfub
cd docfub
virtualenv -p python3 ve3 && source ve3/bin/activate
pip install -r requirements-frozen.txt
```

### Configure

```bash
grep -v IGNORE config.py > local_config.py
nano local_config
```

### Run

```bash
python fs.py
```
