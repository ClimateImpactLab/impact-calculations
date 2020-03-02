# Dependencies

Self-documented input files (MetaCSV and CSVV, or files paired with
FGH files) report a version. When read, this is stored in a
`dependencies` list, which can later be reported in the resulting
output file.

The purpose of dependencies is to facilitate updating. When an input
is changed, the dependencies of all available files can be checked,
and the output file can be regenerated as needed. This process can be
performed recursively, allowing file changes to propagate.
