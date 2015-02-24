## Tutorial ##

After installing MuMax-EC2 ([Linux](install_linux.md), [MacOSX](install_mac.md), [Windows](install_windows.md)) and [setting up your Amazon Web Services (AWS) account](setup_aws.md) you are ready to start the tutorial.

> Throughout using MuMax-EC2, remember that your AWS account will be charged per hour for any running instance. The best practice is to stop or terminate any instance that you are not going to immediately use.

### Accessing the help menu ###

Open a terminal or command prompt and change the directory to where you have stored to MuMax-EC2 software. First lets start by accessing the help menu, where you can look for assistance on the command syntax.

```bash
$ python mumax-ec2 --help
usage: mumax-ec2.py [-h] {run,list,launch,terminate,stop,start} ...

Runs MuMax3 .mx3 files on Amazon Web Services (AWS) instances

positional arguments:
  {run,list,launch,terminate,stop,start}
                        sub-command help
    run                 run help
    list                list help
    launch              launch help
    terminate           terminate help
    stop                stop help
    start               start help

optional arguments:
  -h, --help            show this help message and exit

```

Specific help on sub-commands is accessed in the following way.
```bash
$ python mumax-ec2.py run --help
```

### Running a simulation ###

Simulations are run by passing a MuMax3 .mx3 file to a running GPU instance. The run command automatically selects an existing and ready instance, or prompts you to start one. For now, lets assume you do not have any instances started.

Pass the file path of the .mx3 file into the `run` sub-command. If you do not already have a simulation you can use [Standard Problem 4](https://raw.githubusercontent.com/mumax/3/arne/test/standardproblem4.mx3), implemented by MuMax3.

```bash
$ python mumax-ec2.py run ../tests/standardproblem4.mx3
There are no instances waiting to be used.
Create a new instance for this job? [Yn]: 
```

Answer Yes (Y) to create a new instance.

```bash
Creating a new instance of ami-f0661e98
Waiting for instance i-6e910894 to boot up...
```
There will be a boot time (typically 32 seconds) since you are starting up the instance. This can be avoided by [starting an instance independent of the run command](#starting-an-instance). To cancel the execution of a running simulation use `Ctrl-C` or the equivalent.

```bash
Instance i-6e910894 is ready
Making secure connection to instance i-6e910894...
Transferring input file to instance: standardproblem4.mx3
Starting port forwarding
```
At this point your instance has the simulation file and is about to be started. The software forwards the MuMax3 web-interface, which is accessible through your local browser on [http://127.0.0.1:35367](http://127.0.0.1:35367).

<img src="tutorial_1.png" height="250" style="border: solid 1px #333333; padding: 4px;" />

```
source ./include_cuda && /home/ubuntu/mumax3/mumax3 -f -http=:35367 /home/ubuntu/simulations/standardproblem4.mx3
==================== AWS INSTANCE ====================
//output directory: /home/ubuntu/simulations/standardproblem4.out/
starting GUI at http://127.0.0.1:35367
setgridsize(128, 32, 1)
setcellsize(500e-9/128, 125e-9/32, 3e-9)
Msat = 1600e3
Aex = 13e-12
E_total.get()
Calculating demag kernel 1 %
Calculating demag kernel 100 %
Msat = 800e3
alpha = 0.02
m = uniform(1, .1, 0)
relax()
save(m)
TOL := 1e-5
expectv("m", m.average(), vector(0.9669684171676636, 0.1252732127904892, 0), TOL)
//m[0] : 0.9669655561447144 OK
//m[1] : 0.12528157234191895 OK
//m[2] : 0 OK
tableautosave(10e-12)
autosave(m, 100e-12)
B_ext = vector(-24.6E-3, 4.3E-3, 0)
run(1e-9)
expectv("m", m.average(), vector(-0.9846124053001404, 0.12604089081287384, 0.04327124357223511), TOL)
//m[0] : -0.9846119284629822 OK
//m[1] : 0.12604622542858124 OK
//m[2] : 0.04326914995908737 OK
==================== AWS INSTANCE ====================
Stopping port forwarding
Receiving output files from instance
Removing simulation files from instance
Terminate the instance? [Yn]:
```
The data files have already been transfered to the same directory that contained your .mx3 file. At this point you are asked to terminate the instance. Answering Yes (Y) will permanently remove the instance and its storage. Answering No (N), will give you the option to either keep the instance running or stop the instance. In the case the instance is stopped, you will not be charged for the hourly rate, but may incur minor storage fees. Keeping the instance running allows you to avoid the boot up time on a subsequent simulation. Remember that instances that are not shut down will continue to charge an hourly rate, and it is your responsibility to properly stop or terminate instances.

### Listing instances ###

The importance of knowing what instances are running and which are stopped prompted the `list` sub-command. This allows you to list the AWS ID and IP addresses of the ready, running, and stopped instances.

```bash
$ python mumax-ec2.py list
Mumax-ec2 Instances:
    ID          IP      Status
    i-ab9a7c51  None    (stopped)
```
Above you can see that one instance (AWS ID: i-ab9a7c51) is stopped and can be started for future use.

### Starting an instance ###

Since the boot up time can be a significant time cost, instances can be started directly. There are two methods for starting instances: (1) starting a new instance, and (2) starting a stopped instance using the AWS ID.

(1) Starting a new instance
```bash
$ python mumax-ec2.py launch
```
The optional `--wait` flag keeps the command from returning until the instance is started.

(2) Starting a stopped instance
```bash
$ python mumax-ec2.py start i-ab9a7c51
```

After (2), we can interrogate the instances to see that i-ab9a7c5 is now ready.

```bash
$ python mumax-ec2.py list
Mumax-ec2 Instances:
    ID          IP          Status
    i-ab9a7c51  52.1.87.187 (ready)
```

A subsequent `run` command will automatically use instance i-ab9a7c5 since it is ready.
```bash
$ python mumax-ec2.py run ./tests/standardproblem4.mx3
Instance i-ab9a7c51 is ready
Making secure connection to instance i-ab9a7c51...
Transferring input file to instance: standardproblem4.mx3
...
```

### Stopping an instance ###

Stopping an instance can be achieved through the `stop` sub-command by passing the AWS ID.

```bash
$ python mumax-ec2.py stop i-ab9a7c51
```

### Terminating an instance ###

Terminating an instance is the recommend way to deal with instances upon simulation completion, unless further simulations will immediately follow.

```bash
$ python mumax-ec2.py terminate i-ab9a7c51
```

### Reporting an error ###

If you experience any error in the the operation of MuMax-EC2, make sure to first stop or terminate your instances as appropriate. This can be done manually in the [AWS Console](https://console.aws.amazon.com/console/), under EC2.

Errors should be reported through GitHub on our [Issues page](https://github.com/ralph-group/mumax-ec2/issues).

### Next steps ###

Now you are familiar with all the commands that MuMax3 supports, and are ready to start simulation. For further details on commands, visit the [manual page](manual.md).