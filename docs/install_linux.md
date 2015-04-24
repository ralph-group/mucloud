## Installing on Linux ##

Instructions for installing the necessary Python libraries and MuCloud on Linux are provided.

### Installing Python ###
Python 2.7 is usually already installed through a system package (`python` on Ubuntu). Alternatively it can be installed from the [latest source release](https://www.python.org/downloads/). The [pip installer](https://pip.pypa.io/en/latest/installing.html) is required, which may need to be installed seperately (`python-pip` on Ubuntu).

### Installing MuCloud ###
First, download the [latest release from GitHub](https://github.com/ralph-group/mucloud/releases). Extract the files in a good place and open a terminal in that directory.

```bash
cd /path/to/mucloud
```

Use the pip installer to install the required Python packages.

```bash
pip install -r requirements.txt
```

Change the permissions on `config.ini` to prevent others from reading it.

```bash
chmod 500 config.ini
```

Now you have MuCloud installed. The next step is to [set up the configuration file](setup_aws.md) with your AWS settings to allow access to your account.
