Sage Computation Node
=====================

A Computation Node is a single computer that will do sage computations.  A
computation node is composed of (initially) three seperate processess:

  1. Manager Process (compnode/manager/)
  2. File-Server Process (compnode/fileserver/)
  3. Worker Processes (compnode/worker/)



R > M: EXEC_CELL

{cell-id, ...}

1. Forward to client cmd sock
