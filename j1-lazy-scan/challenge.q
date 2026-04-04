scanz:{[f;init;data]
  n:count data;
  if[n=0; :enlist init];
  .scanz.r:1#init;
  st:{[f;data;n;st]
    r:f[st 0;data st 1];
    .scanz.r,:r 1;
    (r 1;1+st 1;0<>r 0)
  }[f;data;n]/[{[n;st] st[2] and (st 1)<n}[n];(init;0;1b)];
  r:.scanz.r;
  delete r from `.scanz;
  r}
