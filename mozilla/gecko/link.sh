function linkMachrc() {
  local machrc_target=$HOME/.mozbuild/.machrc
  local machrc_source=$(pwd)/gecko/machrc
  LinkFile $machrc_source $machrc_target
}
linkMachrc
