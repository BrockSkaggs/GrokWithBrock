# Transportation Problem With Single Delivery 

## Abstract
Previously, a linear programming model was developed to solve the transportation problem inspired by the supply network of O'Reilly Auto Parts in the southeast United States.  Here a simulated snowfall event triggered excessive demand at the affected stores.  The task was then to satisfy this demand from the surrrounding distribution centers while minimizing the total transportation cost.  This model solved for the optimal solution given the objective and constraints.  A secondary review reveals that there are multiple cases where a store is being satisfied with deliveries from multiple distribution centers.  This may not be desirable.  Hence, this study will take another step and enforce the concept that a store can only be satisfied by a single distribution center.

## Contents
The study is broken into multiple Jupyter notebooks each of which is described below.

- **baseline_solve.ipynb**  Here a baseline is established by solving the classical transportation problem model.  The solution is then reviewed to determine the set of stores that are being satisfied by at least two distribution centers.

- **single_dc_solve.ipynb** This notebook introduces a variation of the transportation model to add the requirement that a store must be satisfied by a single distribution center.

- **single_dc_mip-gap_solve.ipynb** Notebook explores the use of the MIP Gap when solving the same model as introduced in **single_dc_solve.ipynb**.  This allows a high quality solution to be achieved with a greatly reduced solve time.