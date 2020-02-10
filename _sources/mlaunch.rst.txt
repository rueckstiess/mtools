.. _mlaunch:

=======
mlaunch
=======

This tool lets you quickly spin up and monitor MongoDB environments on your
local machine. It supports various configurations of stand-alone servers,
replica sets and sharded clusters. Individual nodes or groups of nodes can
easily be stopped and started again.

In addition to all the listed parameters of **mlaunch** below, you can pass in
any arbitrary options that a ``mongos`` or ``mongod`` binary would understand,
and **mlaunch** will pass them on to the correct binary. This includes the
``-f`` or ``--config`` option to pass on a config file with further options.


Usage
~~~~~

.. code-block:: bash

   mlaunch [-h] [--version] [--no-progressbar]
           {init,start,stop,restart,list,kill} ...


General Parameters
~~~~~~~~~~~~~~~~~~

The following parameters work with all commands.

Help
----
``-h, --help``
   shows the help text and exits.

Version
-------
``--version``
   shows the version number and exits.

Verbosity
---------
``--verbose``
   This will print additional information, depending on each of the commands.

Data directory
--------------
``--dir DIR``
   This parameter changes the directory where **mlaunch** stores its data and
   log files. By default, the directory is the local directory ``./data``,
   below the current working directory.


Commands
~~~~~~~~

``mlaunch`` uses different commands to initialize, stop, start and list test
environments. The general syntax is:

.. code-block:: bash

   mlaunch <command> [--parameters ...]

where ``<command>`` is one of the following choices:

-  ``init``: creates an initial environment and starts all nodes
-  ``stop``: stops some or all nodes in the current environment
-  ``start``: starts some or all nodes in the current environment
-  ``list``: shows a list of the current environment
-  ``kill``: sends a kill (or other) signal to the nodes in the current
   environment

For a given environment (specified by its data directory with the ``--dir``
argument, the default is ``./data``), the ``init`` command only needs to be
called once. ``mlaunch`` stores the configuration in a config file within the
data directory, called ``.mlaunch_startup``. With this file, mlaunch remembers
the configuration and can ``start`` and ``stop`` nodes when required.

-----

init
----

This command initializes and starts MongoDB stand-alone instances, replica
sets, or sharded clusters. It only needs to be called once for each environment
(specified by its data directory with the ``--dir`` argument, the default is
``./data``).

Usage
^^^^^

.. code-block:: bash

   mlaunch init [-h] (--single | --replicaset) [--nodes NUM] [--arbiter]
                [--name NAME] [--priority] [--sharded N [N ...]]
                [--config NUM] [--csrs] [--mongos NUM] [--verbose]
                [--port PORT] [--binarypath PATH] [--dir DIR]
                [--hostname HOSTNAME] [--auth] [--username USERNAME]
                [--password PASSWORD] [--auth-db DB]
                [--auth-roles [ROLE [ROLE ...]]] [--auth-role-docs]
                [--no-initial-user] [--sslCAFile SSLCAFILE]
                [--sslCRLFile SSLCRLFILE] [--sslAllowInvalidHostnames]
                [--sslAllowInvalidCertificates]
                [--sslMode {disabled,allowSSL,preferSSL,requireSSL}]
                [--sslPEMKeyFile SSLPEMKEYFILE]
                [--sslPEMKeyPassword SSLPEMKEYPASSWORD]
                [--sslClusterFile SSLCLUSTERFILE]
                [--sslClusterPassword SSLCLUSTERPASSWORD]
                [--sslDisabledProtocols SSLDISABLEDPROTOCOLS]
                [--sslAllowConnectionsWithoutCertificates] [--sslFIPSMode]
                [--sslClientCertificate SSLCLIENTCERTIFICATE]
                [--sslClientPEMKeyFile SSLCLIENTPEMKEYFILE]
                [--sslClientPEMKeyPassword SSLCLIENTPEMKEYPASSWORD]

For convenience and backwards compatibility, the ``init`` command is the
default command and can be omitted.

Required Parameters
^^^^^^^^^^^^^^^^^^^
The ``init`` command requires **exactly one** of the following two parameters
to run: ``--single`` or ``--replicaset``. They are mutually exclusive and one
must be specified for each ``mlaunch init`` execution.

``--single``
   This parameter will create a single stand-alone node. If ``--sharded`` is
   also specified, this parameter will create each shard as a single
   stand-alone node.

   For example, to start a single ``mongod`` instance on port 27017:

   .. code-block:: bash

      mlaunch --single

``--replicaset``
   This parameter will create a replica set rather than a single node. Other
   :ref:`mlaunch-repl-params` apply and can modify the properties of the
   replica set to launch. If ``--sharded`` is also specified, this parameter
   will create one such replica sets for each shard.

   For example, to start a replica set with (by default) 3 nodes on ports
   27017, 27018, 27019:

   .. code-block:: bash

      mlaunch --replicaset

.. _mlaunch-repl-params:

Replica Set Parameters
^^^^^^^^^^^^^^^^^^^^^^

The following parameters change how a replica set is set up. These parameters
require that you picked the ``--replicaset`` option from the required
parameters.

``--nodes N``
   Specifies the number of data-bearing nodes (arbiters not included) for this
   replica set. The default value is 3.

   For example:

   .. code-block:: bash

      mlaunch --replicaset --nodes 5

   This command starts 5 mongod instances and configures them to one replica
   set.

``--arbiter``
   If this parameter is present, an additional arbiter is added to the replica
   set. Currently, **mlaunch** only supports adding one arbiter. Additional
   arbiters can be started and added to the replica set manually.

   For example:

   .. code-block:: bash

      mlaunch --replicaset --nodes 2 --arbiter

   This command starts 2 data-bearing mongod instances and adds one arbiter to
   the replica set, for a total of 3 voting nodes.

``--name NAME``
   This option lets you modify the name of the replica set. This will change
   both the name and the sub-directory of the ``dbpath``. This option is only
   allowed for a single replica sets and will not work in sharded setups, where
   replica set names are equivalent to the shard names. The default name is
   ``replset``.

   For example:

   .. code-block:: bash

      mlaunch --replicaset --name "my_rs_1"

   This command will create a replica set with the name ``my_rs_1`` and will
   also store the dbpath and log files under ``./data/my_rs_1``.

Sharding Parameters
^^^^^^^^^^^^^^^^^^^

The following parameters influence the setup of a sharded environment. Each
shard will be a copy of the previously specified setup, be it a single instance
or a replica set.

``--sharded S [S ...]``
   If this parameter is provided, sharding is enabled and **mlaunch** will
   create the specified number of shards and add the shards together to a
   sharded cluster. The parameter can work in two ways: Either by specifying a
   single number, which is the number of shards, or by specifying a list of
   shard names.

   For example:

   .. code-block:: bash

      mlaunch --single --sharded 3

   This command will create an environment of 3 shards, each consisting of a
   single stand-alone node. The shard names are ``shard0001``, ``shard0002``,
   ``shard0003``. It will also create 1 config server and 1 mongos per default.

   For example:

   .. code-block:: bash

      mlaunch --replicaset --sharded tic tac toe

   This command will create 3 shards, named ``tic``, ``tac`` and ``toe``. Each
   shard will consist of a replica set of (per default) 3 nodes. It will also
   create 1 config server and 1 mongos per default.

``--config N``
   This parameter determines, how many config servers are launched in a sharded
   environment. The default number is 1. The only valid options for ``N`` are 1
   or 3.

``--csrs``
   This parameter has ``mlaunch`` use `Config Servers as a Replica Set (CSRS)
   <https://docs.mongodb.com/manual/core/sharded-cluster-config-servers/#replica-set-config-servers>`__
   rather than the older Sync Cluster Connection Config (SCCC).

   The CSRS deployment option is supported by MongoDB 3.2+, and as of MongoDB
   3.4 is the default (and only) supported option.

   If you are using MongoDB 3.4 and greater, ``mlaunch`` will use CSRS by
   default.

   *Changed in version 1.2.3*

   CSRS config servers will no longer include incompatible settings, such as:

   -  ``--storageEngine`` -- CSRS config servers will always use WiredTiger.
   -  ``--arbiter`` -- CSRS config servers cannot have any arbiter.

``--mongos N``
   This parameter determines, how many ``mongos`` instances are launched in a
   sharded environment. The default number is 1. With this setting, the default
   can be changed to ``N`` mongos instances.

Authentication Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^

``--auth``
   This parameter enables authentication on your setup. It will transparently
   work with single instances (that require ``--auth``) as well as replica sets
   and sharded environments (that require ``--keyFile``). There is no need to
   additionally specify a keyfile, a random keyfile will be generated for you.

   A username and password will also be set up, either on the mongos for
   sharded environments, or on the primary node for replica sets or on a single
   node.

``--username``
   This parameter changes the default username ``user`` to the specified user.

``--password``
   This parameter changes the default password ``password`` to the specified
   password.

   .. note::

      The default password is chosen deliberately to be easy to remember or
      guess. ``mlaunch`` is meant for testing and issue reproduction, not for
      production use. Even a strong password will not guarantee security with
      mlaunch-generated environments, because the username and password are
      included in the ``data/.mlaunch_startup`` file in clear text.

``--auth-db``
   This parameter changes the default database, from ``admin``, in which the
   user will be created.

   .. note::

      If you change the database, it may not be possible for ``mlaunch`` to
      execute certain commands due to missing privileges. This may lead to
      unexpected behavior for some ``mlaunch`` operations, like for example
      ``mlaunch stop``, which uses the internal ``shutdown`` command. If this
      is the case, use ``mlaunch kill`` instead.

``--auth-roles``
   This parameter changes the initial default roles that the user will receive.
   The default roles are ``dbAdminAnyDatabase``, ``readWriteAnyDatabase``,
   ``userAdminAnyDatabase`` and ``clusterAdmin``. You can provide different
   roles with this parameter, separated by spaces.

   .. note::

      If you change the default roles, it may not be possible for ``mlaunch``
      to execute certain commands due to missing privileges. This may lead to
      unexpected behavior for some ``mlaunch`` operations, like for example
      ``mlaunch stop``, which uses the internal ``shutdown`` command. If this
      is the case, use ``mlaunch kill`` instead.

   For example:

   .. code-block:: bash

      mlaunch --sharded 2 --single --auth --auth-user thomas --auth-password my_s3cr3t_p4ssw0rd

   This command would start a sharded cluster with 2 single shards, 1 config
   server, 1 mongos, and create the user ``thomas`` with password
   ``my_s3cr3t_p4ssw0rd``. It will use the default roles and place the user in
   the ``admin`` database. ``mlaunch`` will

``--auth-role-docs``
   Use with ``--auth-roles`` to interpret roles specified as JSON documents.

``--no-initial-user``
   Do not create an initial user if auth is enabled.

Optional Parameters
^^^^^^^^^^^^^^^^^^^

``--port PORT``
   Uses ``PORT`` as the start port number for the first instance, and increases
   the number by one for each additional instance (mongod/mongos). By default,
   the start port value is MongoDB's standard port 27017. Use this parameter to
   start several setups in parallel on different port ranges.

   For example:

   .. code-block:: bash

      mlaunch --replicaset --nodes 3 --port 30000

   This command would start a replica set of 3 nodes using ports 30000, 30001
   and 30002.

``--binarypath PATH``
   Will set the path where **mlaunch** looks for the binaries of ``mongod`` and
   ``mongos`` to the provided ``PATH``. By default, the $PATH environment
   variable is used to determine which binary is started. You can use this
   option to overwrite the default setting. This is useful for example if you
   compile your own source code and want mlaunch to use the compiled version.

   For example:

   .. code-block:: bash

      mlaunch --single --binarypath ./build/bin

   This command will look for the ``mongod`` binary in ``./build/bin/mongod``
   instead of the default location.

TLS/SSL options
^^^^^^^^^^^^^^^
``--sslCAFile SSLCAFILE``
   Certificate Authority file for TLS/SSL.

``--sslCRLFile SSLCRLFILE``
   Certificate Revocation List file for TLS/SSL.

``--sslAllowInvalidHostnames``
   Allow client and server certificates to provide non-matching hostnames.

``--sslAllowInvalidCertificates``
   Allow client or server connections with invalid
   certificates.

Server TLS/SSL options
^^^^^^^^^^^^^^^^^^^^^^

``--sslMode {disabled,allowSSL,preferSSL,requireSSL}``
   Set the TLS/SSL operation mode.

``--sslPEMKeyFile SSLPEMKEYFILE``
   PEM file for TLS/SSL.

``--sslPEMKeyPassword SSLPEMKEYPASSWORD``
   PEM file password.

``--sslClusterFile SSLCLUSTERFILE``
   Key file for internal TLS/SSL authentication.

``--sslClusterPassword SSLCLUSTERPASSWORD``
   Internal authentication key file password.

``--sslDisabledProtocols SSLDISABLEDPROTOCOLS``
   Comma separated list of TLS protocols to disable [TLS1_0,TLS1_1,TLS1_2].

``--sslAllowConnectionsWithoutCertificates``
   Allow client to connect without presenting a certificate.

``--sslFIPSMode``
   Activate FIPS 140-2 mode.

Client TLS/SSL options
^^^^^^^^^^^^^^^^^^^^^^

``--sslClientCertificate SSLCLIENTCERTIFICATE``
   Client certificate file for TLS/SSL.

``--sslClientPEMKeyFile SSLCLIENTPEMKEYFILE``
   Client PEM file for TLS/SSL.

``--sslClientPEMKeyPassword SSLCLIENTPEMKEYPASSWORD``
   Client PEM file password.

-----

.. _mlaunch-kill:

kill
----

The ``kill`` command stops some or all running nodes in the current
environment, depending on the specified tags, by sending the processes the
``SIGTERM`` (15) signal.

If no tags are specified, ``mlaunch kill`` will kill all nodes. If one or more
tags are specified, ``mlaunch kill`` will only kill the nodes that have all of
the given tags (set intersection). This works even if there is no ``admin``
user with the ``clusterAdmin`` role.

Instead of the ``SIGTERM`` signal, other signals can be specified with the
``--signal`` parameter. (not available on Windows)

Usage
^^^^^

.. code-block:: bash

   mlaunch kill [TAG [TAG ...]] [--signal S] [--dir DIR] [--verbose]


Tag Parameters
^^^^^^^^^^^^^^

The following tags are used with mlaunch, although not all tags are present in
every environment:

-  ``all``: all nodes in the environment.
-  ``running``: all currently running nodes.
-  ``down``: all currently down nodes.
-  ``mongos``: all mongos processes carry this tag.
-  ``mongod``: all mongod processes (including arbiters and config servers).
-  ``config``: all config servers
-  ``shard``: this tag is only used to identify a specific shard number (see
   below).
-  ``<shard name>``: for sharded environments, each member of a shard carries
   the shard name as a tag, e.g. "shard-a".
-  ``primary``: all running primary nodes.
-  ``secondary``: all running secondary nodes.
-  ``arbiter``: all arbiters.
-  ``<port number>``: each node carries its port number as a tag.

If a single tag is specified for the ``kill`` command, the nodes matching this
tag will be killed. If multiple tags are specified, only the nodes matching
**all tags** are killed. Each tag will narrow down the set of matches further.

For example:

.. code-block:: bash

   mlaunch kill

This command kills all running nodes in the current environment.

For example:

.. code-block:: bash

   mlaunch kill mongos

This command kills all running mongos processes in the current environment.

For example:

.. code-block:: bash

   mlaunch kill shard-a secondary

This command kills all running secondary nodes of the shard called 'shard-a' in
the current environment.

For example:

.. code-block:: bash

   mlaunch kill config primary

This command would not kill any nodes, because there is no node with both tags
``config`` and ``primary``.

For example:

.. code-block:: bash

   mlaunch kill 27017

This command would kill the node running on port 27017.

In addition, some tags can be combined with a succeeding number. These tags
are: ``mongos``, ``shard``, ``config``, ``secondary``.

For example:

.. code-block:: bash

   mlaunch kill shard 1

This command kills all members of shard 1 in the current _sharded_ environment.

For example:

.. code-block:: bash

   mlaunch kill shard 2 primary

This command kills the primary of the second shard in the current _sharded_
environment.

For example:

.. code-block:: bash

   mlaunch kill secondary 1

This command kills the first secondary node of all shards if the environment is
_sharded_. If the environment is a _replicaset_, it only applies to the first
secondary.

For example:

.. code-block:: bash

   mlaunch kill

This command sends signal ``SIGTERM`` (15) to all running processes in the
current environment.

For example:

.. code-block:: bash

   mlaunch kill --signal SIGUSR1

This command sends signal ``SIGUSR1`` (30) to all running processes in the
current environment, which in MongoDB causes a log rotation.

-----

.. _mlaunch-start:

start
-----

The ``start`` command starts some or all nodes that are currently down in the
current environment, depending on the specified tags. If no tags are specified,
``mlaunch start`` will start all nodes. If one or more tags are specified,
``mlaunch start`` will only start the nodes that have all of the given tags
(set intersection).

Usage
^^^^^

.. code-block:: bash

   mlaunch start [TAG [TAG ...]] [--dir DIR] [--verbose]

Tag Parameters
^^^^^^^^^^^^^^

The following tags are used with mlaunch, although not all tags are present in
every environment:

-  ``all``: all nodes in the environment.
-  ``running``: all currently running nodes.
-  ``down``: all currently down nodes.
-  ``mongos``: all mongos processes carry this tag.
-  ``mongod``: all mongod processes (including arbiters and config servers).
-  ``config``: all config servers
-  ``shard``: this tag is only used to identify a specific shard number (see
   below).
-  ``<shard name>``: for sharded environments, each member of a shard carries
   the shard name as a tag, e.g. "shard-a".
-  ``arbiter``: all arbiters.
-  ``<port number>``: each node carries its port number as a tag.

Different to the ``stop`` command, there tags for ``primary`` and ``secondary``
are not available for the ``start`` command. This is because the replica set
state of a running node is undetermined.

For examples, see :ref:`mlaunch-stop`.

-----

.. _mlaunch-stop:

stop
----

The ``stop`` command stops some or all running nodes in the current
environment, depending on the specified tags, by sending the ``shutdown``
command to the mongod or mongos instance.

If no tags are specified, ``mlaunch stop`` will stop all nodes. If one or more
tags are specified, ``mlaunch stop`` will only stop the nodes that have all of
the given tags (set intersection).

In authenticated environments, the ``stop`` command requires a user in the
``admin`` database with the ``clusterAdmin`` role. Otherwise the ``stop``
command will not succeed. In that case, you can use the ``kill`` command
instead.

*Changed in version 1.2.3*

As of version 1.2.3, the ``stop`` command is an alias for the ``kill`` command.

For examples, see :ref:`mlaunch-kill`.

Usage
^^^^^

.. code-block:: bash

   mlaunch stop [TAG [TAG ...]] [--dir DIR] [--verbose]

Tag Parameters
^^^^^^^^^^^^^^

The tags for the ``stop`` command are the same as for :ref:`mlaunch-kill`.

-----

restart
-------

The ``restart`` command stops, then restarts some or all nodes in the current
environment, depending on the specified tags. It is added for convenience and
behaves like a ``stop`` and ``start`` command in succession. If no tags are
specified, ``mlaunch restart`` will restart all nodes. If one or more tags are
specified, ``mlaunch restart`` will only restart the nodes that have all of the
given tags (set intersection).


Usage
^^^^^

.. code-block:: bash

   mlaunch restart [TAG [TAG ...]] [--dir DIR] [--verbose]


Tag Parameters
^^^^^^^^^^^^^^

See :ref:`mlaunch-start` and :ref:`mlaunch-stop`.

-----

list
----

The ``list`` command shows an overview of all nodes in the current environment,
as well as their status (running/down) and port. With the optional
``--verbose`` flag, the list command also shows all tags for each node.


Usage
^^^^^

.. code-block:: bash

   mlaunch list [--dir DIR] [--startup] [--tags]

For example:

.. code-block:: bash

   mlaunch list

   PROCESS          STATUS     PORT

   mongos           running    27017
   mongos           running    27018

   config server    running    27025
   config server    running    27026
   config server    down       27027

   shard01
       primary      running    27019
       secondary    running    27020
       arbiter      running    27021

   shard02
       mongod       down       27022
       mongod       down       27023
       mongod       down       27024

This command displays a list of all nodes, their status and port number. In
this case, the environment was started with:

.. code-block:: bash

   mlaunch --sharded 2 --replicaset --nodes 2 --arbiter --config 3 --mongos 2

Optional Parameters
^^^^^^^^^^^^^^^^^^^

``--tags``
   This option additionally shows a column with all the tags that the instance
   can be addressed with. Tags can be used to target certain instances for
   ``start``, ``stop``, ``kill``, etc. commands.

   For example:

   .. code-block:: bash

      mlaunch list --tags

      PROCESS      STATUS     PORT     TAGS

      primary      running    27017    27017, all, mongod, primary, running
      secondary    running    27018    27018, all, mongod, running, secondary
      mongod       down       27019    27019, all, down, mongod

   This command displays a list of all nodes, their status and port number, and
   in addition, their tags. In this case, the environment was started with:

   .. code-block:: bash

      mlaunch --replicaset

``--startup``
   This option additionally shows a column with the startup strings that was
   used to run the given instance. This is useful to if an instance needs to be
   started manually.

   For example:

   .. code-block:: bash

      mlaunch list --startup

      PROCESS      PORT     STATUS     PID     STARTUP COMMAND

      secondary    27017    running    4264    mongod --replSet replset --dbpath /tmp/data/replset/rs1/db --logpath /tmp/data/replset/rs1/mongod.log --port 27017 --logappend --fork -vv
      mongod       27018    running    4267    mongod --replSet replset --dbpath /tmp/data/replset/rs2/db --logpath /tmp/data/replset/rs2/mongod.log --port 27018 --logappend --fork -vv
      mongod       27019    running    4270    mongod --replSet replset --dbpath /tmp/data/replset/rs3/db --logpath /tmp/data/replset/rs3/mongod.log --port 27019 --logappend --fork -vv

   This command displays a list of all nodes, their status and port number, and
   in addition, their startup commands.

Disclaimer
~~~~~~~~~~

This software is not supported by `MongoDB, Inc. <https://www.mongodb.com>`__
under any of their commercial support subscriptions or otherwise. Any usage of
mtools is at your own risk. Bug reports, feature requests and questions can be
posted in the `Issues
<https://github.com/rueckstiess/mtools/issues?state=open>`__ section on GitHub.