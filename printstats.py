import pstats 
p = pstats.Stats('stats')
# p.strip_dirs().sort_stats('time').print_stats(30)
p.strip_dirs().sort_stats('cumulative').print_stats(30)