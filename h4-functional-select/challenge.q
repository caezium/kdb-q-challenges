/ h4-functional-select
/ Implement qbuild: construct a functional select parse tree from a spec dict.

qbuild:{[spec] wc:spec`c; gb:spec`b; ag:spec`a; pw:{parse x} each wc; w:$[0=count wc; (); 1=count wc; enlist enlist first pw; enlist pw]; b:$[0=count gb; 0b; ({x!x} gb)]; a:$[((99h=type ag) and 0<count key ag); (key ag)!{parse x} each value ag; ()]; (?;spec`t;w;b;a)}
