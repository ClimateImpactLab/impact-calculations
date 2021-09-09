The singularity definition file is in `helpers/gcp-generate.def`.  You can generate it on a server with sudo-access and singularity using:
```
sudo singularity build gcp-generate.img gcp-generate.def
```

## Design choices:

The containerization produces a single file, called gcp-generate.img.  This acts like an executable, which runs a single generate.sh process.  It cannot be (immediately) used to run aggregate or any other GCP code.  Each system (Sacagawea, BRC, ...) would have a single copy of this container file.

(It is possible to set it up to run multiple processes in one file, or to run other operations than generate, but only at the expense of having a more complicated usage process.)

The container has python, various system libraries, as well as two GCP-specific libraries: metacsv and impactlab-tools.  These libraries are shared across all sectors and analyses that use the containers.  In this way, it can replace virtualenv.

Since versions of impact-calculations, open-estimate, and impact-common frequently change across analyses, these are not locked in as part of the container.  Instead, these three repositories must exist in the directory that gcp-generate.img is being run from, with their default names ("impact-calculations", etc.).

## Running and testing it:

To generate results using the container, you need to have a directory containing the impact-calculations, open-estimate, and impact-common repositories, and the server.yml file.  You also need to know where the container lives.  Let's call this /X/gcp-generate.img.

1. Navigate to the directory containing impact-calculations.
2. Run: `export SINGULARITY_BINDPATH=X` where X is defined as above.
3. To produce a single generation process, run `/X/gcp-generate.img <config/path.yml> <other options>`.  <config/path.yml> should be a path to a run configuration file; if it is a relative path, it should be relative to the impact-calculations directory.  <other options> can be anything else you like to use, if you're in the habit of passing other options.  Examples are --filter-region=USA.14.608 --outputdir=$PWD/temp.  However, you cannot specify a number for multiple processes here.
