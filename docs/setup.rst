Setting up AWS
==============

Instructions for setting up your Amazon Web Services (AWS) account to use with MuCloud are provided, which follow the `installation step`_.

.. _installation step: install.html

Making a user
-------------

Begin by `signing up`_ for an Amazon Web Services account.


.. image:: _static/aws_1.png
    :class: bordered-image

After your account has been created, open the `AWS Console`_.

.. image:: _static/aws_2.png
    :class: bordered-image

Since the Amazon Machine Image (AMI) for MuCloud is in the US East (N. Virginia) region, choose that region in the upper right hand dropdown.

.. image:: _static/aws_2_1.png
    :class: bordered-image

Choose IAM (Identity and Access Management) > Users > Create New Users.

.. image:: _static/aws_3.png
    :class: bordered-image

Create a user "mucloud" (leave "Generate access key for each user" checked). Show the User Security Credentials, and copy the "Access Key ID" (``AccessID``) and "Secret Access Key" (``SecretKey``) into the MuCloud ``config.ini`` that came with the latest release. 

.. image:: _static/aws_4.png
    :class: bordered-image

Download the credentials and keep them in a safe place. Close to return to the Users menu.

Under Users > mucloud, Attach User Policy.

.. image:: _static/aws_5.png
    :class: bordered-image

Search and select "AmazonEC2FullAccess". Attach this policy to the "mucloud" user.

.. image:: _static/aws_6.png
    :class: bordered-image

Now your "mucloud" user has been created and has full permission to use EC2, without allowing access to any other AWS services for security reasons.

.. _AWS Console: https://console.aws.amazon.com/console/
.. _signing up: https://console.aws.amazon.com/console/home


Getting a private key
---------------------

From the AWS Console, open up EC2.

.. image:: _static/aws_2.png
    :class: bordered-image

Choose Key Pairs > Create Key Pair. Create a key pair with name "mucloud", and update ``config.ini`` (``PrivateKeyName``) with this name.

.. image:: _static/aws_7.png
    :class: bordered-image

Download the ``.pem`` file and save it to a safe place. On Linux and MacOSX change the permissions of the ``.pem`` file to prevent others from reading it.

    chmod 500 mucloud.pem

Update ``config.ini`` with the path of the ``.pem`` private key (``PrivateKeyFile``). Now you have a private key with which you can connect to your instance with SSH.

Creating a security group
-------------------------

From EC2, choose Security Groups > Create Security Group.

.. image:: _static/aws_8.png
    :class: bordered-image

Set the security group name to "mucloud", and update ``config.ini`` (``SecurityGroups``) with this name. A description is required by AWS. On the Inbound tab > Add Rule > "Type: SSH".

For the best security, choose "Source: My IP". Note that if your IP changes, **you will have to edit the security group again to update the IP.** Alternatively "Source: Anywhere" can be used.


Verify your image
-----------------

The ``Image`` setting in ``config.ini`` specifies the Amazon Machine Image (AMI) that GPU instances are created from. Check the `release page`_ to ensure that you have the latest AMI for your version of MuCloud. The public AMIs are only avalible in the U.S. East region. Advanced users can make their own custom AMIs to extend the features of MuCloud or `copy them to a different region`_.

After you checked that you have the latest AMI, your AWS account has been set up properly and your ``config.ini`` file has been updated. The next step is to start using MuCloud, or `follow the tutorial`_ to get started.

.. _release page: https://github.com/ralph-group/mucloud/releases
.. _copy them to a different region: https://aws.amazon.com/blogs/aws/ec2-ami-copy-between-regions/
.. _follow the tutorial: tutorial.html