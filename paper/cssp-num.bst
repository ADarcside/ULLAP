% cssp-num.bst: numeric, citation-ordered references in the layout of published
% Circuits, Systems, and Signal Processing articles:
%   1. N. Bertin, E. Camberlein, Title. Journal 33(2), 100--110 (2020). https://doi.org/...
ENTRY { author title journal volume number pages year doi url note } {} { label }
INTEGERS { nameptr namesleft numnames }
STRINGS { s t }

FUNCTION {not} { { #0 } { #1 } if$ }
FUNCTION {and} { 'skip$ { pop$ #0 } if$ }
FUNCTION {field.or.null} { duplicate$ empty$ { pop$ "" } 'skip$ if$ }

FUNCTION {format.names}
{ 's :=
  #1 'nameptr :=
  s num.names$ 'numnames :=
  numnames 'namesleft :=
  { namesleft #0 > }
  { s nameptr "{f{.}.~}{vv~}{ll}{, jj}" format.name$ 't :=
    nameptr #1 >
      { t "others" = { ", et~al." * } { ", " * t * } if$ }
      't
    if$
    nameptr #1 + 'nameptr :=
    namesleft #1 - 'namesleft :=
  }
  while$
}

FUNCTION {n.dashify}
{ 't := ""
  { t empty$ not }
  { t #1 #1 substring$ "-" =
      { t #1 #2 substring$ "--" = not
          { "--" * t #2 global.max$ substring$ 't := }
          { { t #1 #1 substring$ "-" = }
            { "-" * t #2 global.max$ substring$ 't := }
            while$
          }
        if$
      }
      { t #1 #1 substring$ * t #2 global.max$ substring$ 't := }
    if$
  }
  while$
}

FUNCTION {article}
{ newline$
  "\bibitem{" cite$ * "}" * write$ newline$
  author empty$ { "" } { author format.names ", " * } if$
  title field.or.null * ". " *
  journal field.or.null *
  volume empty$ 'skip$ { " \textbf{" * volume * "}" * } if$
  number empty$ 'skip$ { "(" * number * ")" * } if$
  pages empty$ 'skip$ { ", " * pages n.dashify * } if$
  year empty$ 'skip$ { " (" * year * ")" * } if$
  "." *
  doi empty$
    { url empty$ 'skip$ { " \url{" * url * "}" * } if$ }
    { " \url{https://doi.org/" * doi * "}" * }
  if$
  note empty$ 'skip$ { " " * note * } if$
  write$ newline$
}
FUNCTION {misc} { article }
FUNCTION {default.type} { article }

READ
FUNCTION {begin.bib}
{ "\begin{thebibliography}{99}" write$ newline$ }
FUNCTION {end.bib}
{ newline$ "\end{thebibliography}" write$ newline$ }
EXECUTE {begin.bib}
ITERATE {call.type$}
EXECUTE {end.bib}
