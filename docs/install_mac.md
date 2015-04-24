## Installing on MacOSX ##

Instructions for installing the necessary Python libraries and MuCloud on MacOSX are provided.

### Installing Python ###

OS X Mavericks ships with Python 2.7.5, and OS X Yosemite with 2.7.6. Either version is capable of running MuCloud, though both will require that you manually install pip according to [these instructions](https://pip.pypa.io/en/latest/installing.html#install-pip). In order to separate the system python packages from those you are about to install, you may consider using a [virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/). 

### Installing XCode ###

The [XCode development environment](https://developer.apple.com/xcode/downloads/) is required for compilation of C/C++ code included in many Python packages. It can be installed from the App Store. 

### Installing MuCloud ###
First, download the [latest release from GitHub](https://github.com/ralph-group/mucloud/releases). Extract the files in a good place and open a terminal in that directory.

```bash
cd /path/to/mucloud
```

Use the pip installer to install the required Python packages. Depending on which Python distribution you are using, you make have to preface the `pip` commands with `sudo` (though you may once again consider a virtual environment.)

```bash
pip install -r requirements.txt
```
With certain versions of Xcode, at least 5.1 and 5.2, you may need to downgrade a particular error to a warning in order for compilation of pycrypto (one of the requirements) to succeed. This [can be accomplished](https://kaspermunck.github.io/2014/03/fixing-clang-error/) by setting the `ARCHFLAGS` environment variable and passing it to the sudo environment with the `-E` flag.

```bash
export ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future
sudo -E pip install pycrypto 
sudo pip install -r requirements.txt
```

If you have established a Python environment that does not require root access for package installation, the `sudo` command and `-E` flag are not required.

Finally, change the permissions on `config.ini` to prevent others from reading it.

```bash
chmod 500 config.ini
```

Now you have MuCloud installed. The next step is to [set up the configuration file](setup_aws.md) with your AWS settings to allow access to your account.
