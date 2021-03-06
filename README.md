MuCloud
=======

> **NOTE:** Many changes have occurred since this tool was developed, in both AWS and Python. This project is not being actively maintained and will be archived for further reference. We hope that it still provides a useful example for how to run simulations on cloud resources.

This software allows [MuMax3](http://mumax.github.io/) GPU-accelerated micromagnetic simulations to be run on a computer without a GPU card. With your [Amazon Web Services](http://aws.amazon.com/) (AWS) account, virtual computer instances are created using the [Elastic Compute Cloud](http://aws.amazon.com/ec2/) (EC2). These instances provide on-demand ([price per hour](http://aws.amazon.com/ec2/pricing/)) access to physical GPU hardware, that allow the simulations to be run remotely. The script interface mimics MuMax3, so that working with MuCloud is as easy as using MuMax3 on a local computer.

**Authors:** Colin Jermain, Graham Rowlands  
**License:** [MIT License](http://opensource.org/licenses/MIT)   
**Version:** 1.2 (supports MuMax 3.9c)

**Instructions:** http://ralph-group.github.io/mucloud

**Requirements:** Amazon Web Services account

Below is an example of running Standard Problem 4 with MuCloud on a Windows machine.

<img src="docs/_static/standard_problem_4.gif" />
