mumax-ec2
=========

Cross-platform script for running Mumax3 on Amazon Web Services (AWS) Elastic Compute Cloud (EC2).

Authors: Colin Jermain, Graham Rowlands  
License: [MIT License](http://opensource.org/licenses/MIT)

### Install

#### Installing the required libraries
TODO: Write this section

#### Getting the script
1. Download the [latest release from GitHub](https://github.com/ralph-group/mumax-ec2/releases).
2. On Linux or MacOSX change the permissions on `config.ini` to prevent others from reading it

```bash
chmod 500 config.ini
```

3. Open `config.ini` for editing in the next section

Now you have the script installed. The next step is to set up the configuration file with your AWS settings to allow access to your account.

#### Setting up AWS
1. [Sign up](https://aws.amazon.com/) for an Amazon Web Services (AWS) account
2. Open the [AWS Console](https://console.aws.amazon.com/console/)
3. Choose IAM (Identity and Access Management) > Users > Create New Users
4. Create a user "mumax-ec2" (leave "Generate access key for each user" checked)
5. Show User Security Credentials
6. Copy the "Access Key ID" into `config.ini` (`AccessID`)
7. Copy the "Secret Access Key" into `config.ini` (`SecretKey`)
8. Download Credentials and keep them in a safe place > Close
9. Under Users > mumax-ec2, Attach User Policy
10. Select "Amazon EC2 Full Access" and Apply Policy

Now your "mumax-ec2" user has been created and has full permission to use EC2, without allowing access to any other AWS services for security reasons.

11. From the AWS Console, choose EC2
12. Choose Key Pairs > Create Key Pair
13. Create a key pair with name "mumax-ec2", and update `config.ini` (`PrivateKeyName`) with this name
14. Download the `.pem` file and save it to a safe place
15. On Linux or MacOSX change the permissions of the `.pem` file to prevent others from reading it

```bash
chmod 500 mumax-ec2.pem
```

16. Update `config.ini` with the path to the private key (`PrivateKeyFile`)

Now you have a private key with which you can connect to your instance with SSH.

17. From EC2, choose Security Groups > Create Security Group
18. Set the security group name to "mumax-ec2", and update `config.ini` (`SecurityGroups`) with this name
19. Add a description
20. Inbound tab > Add Rule > Type: SSH

For the best security, choose Source: My IP. Note that if your IP changes, you will have to edit the security group again to update the IP. Alternatively Source: Anywhere can be used.

21. Create the security group

Now you are ready to go!


### Usage

```
python mumax-ec2.py input_filename.mx3
```


### Virtual Environment

The Python virtual environment can be created with necessary libraries through pip by using the requirements.txt file in the main part of the directory.

```
$ pip install -r requirements.txt
```
