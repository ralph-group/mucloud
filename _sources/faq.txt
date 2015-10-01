FAQ
===

What happens if I get the error ``The image id '[ami-...]' does not exist``?

    This occurs because the AMI, specified in your ``config.ini`` file, is out of date with the current AMI for your version of MuCloud. The latest AMI for a particular version of MuCloud can be found on the `release page`_.

.. _release page: https://github.com/ralph-group/mucloud/releases

Can I use a region other than U.S. East?

    The public AMI that is provided with MuCloud is only accessible for the U.S. East region. If you copy that AMI into your own account, you can `transfer it to another region`_. Keep in mind that there is a storage cost for the AMI content.

.. _transfer it to another region: https://aws.amazon.com/blogs/aws/ec2-ami-copy-between-regions/