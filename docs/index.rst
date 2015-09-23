MuCloud
=======

MuCloud runs `MuMax3`_ GPU-accelerated micromagnetic simulations on the cloud, eliminating the need to have a GPU card on your computer. 

.. image:: _static/concept.png

With your `Amazon Web Services`_ (AWS) account, virtual computer instances are created using the `Elastic Compute Cloud`_ (EC2). These instances provide on-demand (`price per hour`_) access to physical GPU hardware, that allow the simulations to be run remotely. The script interface mimics MuMax3, so that working with MuCloud is as easy as using MuMax3 on a local computer.

.. _MuMax3: http://mumax.github.io/
.. _Amazon Web Services: http://aws.amazon.com/
.. _Elastic Compute Cloud: http://aws.amazon.com/ec2/
.. _price per hour: http://aws.amazon.com/ec2/pricing/

Citing
------
If you make significant use of this program, we kindly ask that you cite:

    *GPU-accelerated micromagnetic simulations using cloud computing*, `arXiv:1505.01207`__ (2015)

.. __: http://arxiv.org/abs/1505.01207

Usage
-----
A `full tutorial`_ is provided to get you started that covers all the functionality of the program. Below is an example of running Standard Problem 4 with MuCloud on a Windows machine.

.. image:: _static/standard_problem_4.gif

.. _full tutorial: tutorial.html


.. toctree::
   :hidden:
   :maxdepth: 2
   
   install
   setup
   tutorial
   faq
   changelog
   license