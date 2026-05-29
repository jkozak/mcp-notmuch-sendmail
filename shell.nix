{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.notmuch
  ];

  shellHook = ''
    export LD_LIBRARY_PATH="${pkgs.notmuch}/lib''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  '';
}
