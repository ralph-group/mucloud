## Installing on MacOSX ##

The simplest method of running MuCloud is with the [latest executable version](https://github.com/ralph-group/mucloud/releases). Alternatively, the following instructions illustrate how to install the necessary Python libraries on MacOSX to run MuCloud from the source.

### Installing Python ###

OS X Mavericks and Yosemite ship with Python 2.7.5 and 2.7.6 respectively, which are both capable of running MuCloud. Follow the [instructions for installing pip](https://pip.pypa.io/en/latest/installing.html#install-pip), which is the Python program for installing dependent packages.

### Installing Xcode ###

The [Xcode development environment](https://developer.apple.com/xcode/downloads/) is required for compilation of C/C++ code included in many Python packages. It can be installed from the App Store. 

### Installing MuCloud ###
First, download the [latest release from GitHub](https://github.com/ralph-group/mucloud/releases). Extract the files in a good place and open a terminal in that directory.

```bash
cd /path/to/mucloud
```

Use the pip installer to install the required Python packages. Optionally, a [virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/) can be used to separate the system packages from MuCloud dependencies. Preface the `pip` commands with `sudo` if you are not using a virtual environment.

```bash
sudo pip install -r requirements.txt
```
With certain versions of Xcode, at least 5.1 and 5.2, you may need to downgrade a particular error to a warning in order for compilation of the required package, `pycrypto`. This [error can be downgraded](https://kaspermunck.github.io/2014/03/fixing-clang-error/) by setting the `ARCHFLAGS` environment variable and passing it to the sudo environment with the `-E` flag.

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
