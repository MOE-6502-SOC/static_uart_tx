# \<Component Title here\>
***Remove this note:*** *This repository is a template repository in which all*
*components of the [MOE-6502-SOC](https://github.com/MOE-6502-SOC) organization*
*should share its basic structure. Each component may have additional structure*
*elements, but no component shall remove one of the given directories.*

\<Breif component description here\>


***Remove this note:*** *Most of the below notes could be kept, but it is not*
*a requirement. It is recommended to leave only links to each directory. It is*
*required to keep the link to the documentation folder and the back-link to this*
*repository.*
## Repository Structure

**For a more detailed description of the structure of this repository, see**
[MOE-6502-SOC/component](https://github.com/MOE-6502-SOC/component).

**Documentation is in the** [`doc`](./doc) directory.
  - All documentation related to the component shall go in this directory.
  This includes a *component specification*, *test plan documentation*,
  *build procedure docs*, etc. **Put all documentation in this directory.**

**Build files are in the** [`build`](./build) directory.
  - This directory shall include all scripts and supporting files for build of
  the design. **In many cases, this folder may be empty. Such as components**
  **which do not make up an entire design.**

**Dependency files are in the** [`lib`](./lib) directory.
  - This directory shall contain dependencies for building of the component.
  **This directory should be empty under *most* circumstances while being tracked.**
  **That is, this directory should only contain items after the dependency**
  **management system has placed all dependencies here.**

**Source files are in the** [`src`](./src) directory.
  - This directory shall only include source files required for the
  instantiation of the component in a design. This includes *dependency lists*
  *for managing dependencies for builds and tests*, *rtl files*, *constaints*
  *files*, etc. **In all cases, where constraints exist, a subdirectory shall**
  **be made which contains them, `src/constraints`**.

**Test files are in the** [`test`](./test) directory.
  - This directory shall include only code related to performing unit tests.
  This includes scripts for *test automation*, *test code*, etc.
