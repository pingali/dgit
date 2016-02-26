dgit FAQ
--------

1. What is dgit? 

   dgit is a wrapper around git to create and manage dataset repositories. 

2. Why not git and github? 

   Code and data are different - scale, nature, workflows etc. 

   We started this work with git and github, and quickly realized that
   code and data are different. As the scale of datasets (size,
   number) increases, github costs are prohibitive.  Also that:
   
   * We need to operate on two repositories simultaneously - one code
     repo and one data repo. We cant have one repo for both because
     code and data have different characteristics - development,
     sharing, and application.

   * A single code repo may generate arbitrary number of datasets,
      each of which may have one or more files. It is not unusual to
      have each script generating one dataset during each run 

   * Data has stronger or different requirements in terms of security
     than code. The workflows are different. Datasets obtained from
     thirdparties (e.g., credit scores) require custom policies to be
     implemented.

3. Can I extend this with my own backend? 

   Sure. You can add repository managers (e.g., bzr, svn), backends
   (e.g., network file system, dropbox etc.), and instrumentation
   (e.g., extract model parameters)

