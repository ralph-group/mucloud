MuMax-EC2
=========

This software allows [MuMax3](http://mumax.github.io/) GPU-accelerated micromagnetic simulations to be run on a computer without a GPU card. MuMax-EC2 uses your [Amazon Web Services](http://aws.amazon.com/) (AWS) Elastic Compute Cloud (EC2) account to connect to on-demand virtual computers (instances) that have GPU hardware, which are offered over the Internet for a fixed hourly price. Our command line program simplifies the process of using AWS and mimics the standard MuMax3 operation, including the web-based interface. The program is available for Linux, MacOSX, and Windows computers.

Authors: Colin Jermain, Graham Rowlands  
License: [MIT License](http://opensource.org/licenses/MIT)

Instructions can be found at:  
http://ralph-group.github.io/mumax-ec2

Requirements:   
    Amazon Web Services account   
    Python 2.7   

Below is an example of running Standard Problem 4 with MuMax-EC2 on a Windows machine.

<img src="standard_problem_4.gif" />