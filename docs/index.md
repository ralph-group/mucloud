## MuMax-EC2 ##

This software allows [MuMax3](http://mumax.github.io/) GPU-accelerated micromagnetic simulations to be run on a computer without a GPU card. With your [Amazon Web Services](http://aws.amazon.com/) (AWS) account, virtual computer instances are created using the [Elastic Compute Cloud](http://aws.amazon.com/ec2/) (EC2). These instances provide on-demand ([price per hour](http://aws.amazon.com/ec2/pricing/)) access to physical GPU hardware, that allow the simulations to be run remotely. The script interface mimics MuMax3 and also forwards the web-based interface, so working with MuMax-EC2 is as easy as MuMax3.

Authors: Colin Jermain, Graham Rowlands  
License: [MIT License](license.md)   
Source code: [ralph-group/mumax-ec2](http://www.github.com/ralph-group/mumax-ec2) on GitHub

## Installing ##

MuMax-EC2 requires an AWS account and Python 2.7. Instructions for setting up and installing the program are provided depending on your operating system.

<table>
    <tr>
        <td style="padding-right: 1em; text-align: center">
            <a href="install_linux.md" style="color: #153549; text-decoration: underline">
            <div style="font-size: 4em; line-height: 1.5em;">
                <i class="fa fa-linux"></i>
            </div>
            Linux
            </a>
        </td>
        <td style="padding-right: 1em; text-align: center">
            <a href="install_mac.md" style="color: #153549; text-decoration: underline">
            <div style="font-size: 4em; line-height: 1.5em;">
            <i class="fa fa-apple"></i>
            </div> 
            MacOSX
            </a>
        </td>    
        <td style="padding-right: 1em; text-align: center">
            <a href="install_windows.md" style="color: #153549; text-decoration: underline">
            <div style="font-size: 4em; line-height: 1.5em;">
                <i class="fa fa-windows"></i>
            </div>
            Windows
            </a>
        </td>
    </tr>
</table>


## Usage ##

A [full tutorial](tutorial.md) is provided to get you started that covers all the functionality of the program. 

Below is an example of running Standard Problem 4 with MuMax-EC2 on a Windows machine.

<img src="standard_problem_4.gif" />