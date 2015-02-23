## Installing on MacOSX ##

Instructions for installing the necessary Python libraries and MuMax-EC2 on MacOSX are provided.

### Installing Python ###


Install pip by easy_installing the pip tar.gz.

With Xcode 5.1, you may need to downgrade certain warning to errors. That can be accomplished by introducing the following environment variable (https://kaspermunck.github.io/2014/03/fixing-clang-error/), and making sure it is available when you run easy_install with sudo.

export ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future
sudo -E pip install pycrypto 
sudo pip install -r requirements.txt

otherwise just run:

sudo pip install pycrypto 
sudo pip install -r requirements.txt

Presently, instances that show up as terminated in the AWS console are showing as “stopped” in the script output. Maybe we should be consistent with our terminology?




### Installing MuMax-EC2 ###
First, download the [latest release from GitHub](https://github.com/ralph-group/MuMax-EC2/releases). Extract the files in a good place and open a terminal in that directory.

```bash
cd /path/to/mumax-ec2
```

Use the pip installer to install the required Python packages.

```bash
pip install -r requirements.txt
```

Change the permissions on `config.ini` to prevent others from reading it.

```bash
chmod 500 config.ini
```

Now you have MuMax-EC2 installed. The next step is to [set up the configuration file](setup_aws.md) with your AWS settings to allow access to your account.
