<h2>Micromagnetic simulations on cloud computing</h2>

This software allows [MuMax3](http://mumax.github.io/) GPU-accelerated micromagnetic simulations to be run on a computer without a GPU card. With your [Amazon Web Services](http://aws.amazon.com/) (AWS) account, virtual computer instances are created using the [Elastic Compute Cloud](http://aws.amazon.com/ec2/) (EC2). These instances provide on-demand ([price per hour](http://aws.amazon.com/ec2/pricing/)) access to physical GPU hardware, that allow the simulations to be run remotely. The script interface mimics MuMax3, so that working with MuCloud is as easy as using MuMax3 on a local computer.

<div style="display: block;">
<div class="col-sm-5">
<br />
    <ul class="list-group">
        <li class="list-group-item">Authors: Colin Jermain, Graham Rowlands</li>
        <li class="list-group-item">License: <a href="/license/">MIT License</a></li>
        <li class="list-group-item">Source: 
            <a href="http://www.github.com/ralph-group/mucloud">
            <i class="fa fa-code"></i>
            ralph-group/mucloud</a> on GitHub</li>
        <li class="list-group-item">Latest Version: 
            <a href="https://github.com/ralph-group/mucloud/releases">1.2</a></li>
     </ul>
</div>

<div class="col-sm-6">
<h3>Citing</h3>

If you make significant use of this program, we kindly ask that you cite:<br />
<a href="http://arxiv.org/abs/1505.01207"><i class="fa fa-file-o"></i>
 "GPU-accelerated micromagnetic simulations using cloud computing", arXiv:1505.01207 (2015)</a>
 <br /><br /><br /><br />
</div>
</div>

### Installing ###

MuCloud is offered as a stand-alone executable or a bundle of Python source files. Choose your operating system below to download the latest executable, and then follow the instructions for <a href="/setup_aws/">setting up your AWS account</a>. Instructions for installing the program and setting up your AWS account are provided depending on your operating system.

<form action="/install_linux/" style="display: inline";>
<button class="btn btn-default btn-default">
    <div style="font-size: 2em; line-height: 1.5em;">
    <i class="fa fa-linux"></i>
    </div>
    Linux
</button>
</form>
<form action="/install_mac/" style="display: inline";>
<button class="btn btn-default btn-default">
    <div style="font-size: 2em; line-height: 1.5em;">
    <i class="fa fa-apple"></i>
    </div>
    MacOSX
</button>
</form>
<form action="/install_windows/" style="display: inline";>
<button class="btn btn-default btn-default">
    <div style="font-size: 2em; line-height: 1.5em;">
    <i class="fa fa-windows"></i>
    </div>
    Windows
</button>
</form>

### Usage ###

A [full tutorial](tutorial.md) is provided to get you started that covers all the functionality of the program. 

Below is an example of running Standard Problem 4 with MuCloud on a Windows machine.

<img src="standard_problem_4.gif" />