class Main : Object {
  run
    [ |
      result := self double: 21.
      _ := result print.
    ]
  
  double:
    [ :n |
      r := n plus: n.
    ]
}
