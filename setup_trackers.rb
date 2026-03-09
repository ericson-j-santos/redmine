# Criar trackers padrão
trackers_data = [
  {name: 'Bug', default_status_id: 1, position: 1},
  {name: 'Task', default_status_id: 1, position: 2},
  {name: 'Feature', default_status_id: 1, position: 3}
]

trackers_data.each do |data|
  tracker = Tracker.create!(data)
  puts "Tracker criado: #{tracker.name} (ID: #{tracker.id})"
end

# Associar ao projeto
project = Project.find_by(identifier: 'proposta-suite')
project.trackers = Tracker.all
project.save!
puts "\nTrackers associados ao projeto: #{project.trackers.pluck(:name).join(', ')}"
