mumax-ec2
=========

This software allows [MuMax3](http://mumax.github.io/) GPU-accelerated micromagnetic simulations to be run on a computer without a GPU. The [Amazon Web Services](http://aws.amazon.com/) (AWS) Elastic Compute Cloud (EC2) is used for its GPU hardware, which provides on-demand virtual computers which are attached to the physical hardware that accelerates the simulation. The interface mimics MuMax3 and also forwards the web-based interface.

Authors: Colin Jermain, Graham Rowlands  
License: [MIT License](http://opensource.org/licenses/MIT)

### Install

Instructions can be found at:  
https://github.com/ralph-group/mumax-ec2/wiki/Installing-mumax-ec2

Requirements:
    Amazon Web Services account
    Python 2.7

### Usage

```
python mumax-ec2.py input_filename.mx3
```
