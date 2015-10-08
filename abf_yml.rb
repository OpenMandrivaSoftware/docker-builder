#!/usr/bin/env ruby
require 'yaml'
require 'optparse'

project_path = ''
OptionParser.new do |o|
  o.on('-p project_path') { |p| project_path = p }
  o.parse!
end

abf_yml = "#{project_path}/.abf.yml"
if File.exists?(abf_yml)
  file = YAML.load_file(abf_yml)
  file['sources'].each do |k, v|
    puts "==> Downloading '#{k}'..."
    system "curl -L http://file-store.rosalinux.ru/api/v1/file_stores/#{v} -o #{project_path}/#{k}"
    puts "Done."
  end
end
