# Variant-planner

cd lake

mkdir -p variants genotypes/samples/


# Split 'INPUT_hg19_annovar_MPA.vcf.gz' by sample:
sampl=B00GMSJ && \
	bcftools view -s $sampl examples/*vcf.gz 2> /dev/null | bcftools view -i 'GT="alt"' -Oz -o ${sampl}.vcf.gz

# And the same for remaining 2


# Convert to parquet:
ls -d ../examples/B*gz |
	xargs basename -a -s .vcf.gz |
	parallel --dry-run \
		"variantplaner -t 4 vcf2parquet -i ../examples/{}.vcf.gz variants -o variants/{/}.parquet genotypes -o genotypes/samples/{/}.parquet"


# Merge variants
variantplaner -t 8 struct -i variants/*.parquet -- variants -o uniq_variants/


# Organise GT by variants:
mkdir -p genotypes/variants/ # -> Useless ? Dir is actually 'genotypes/partitions' ???
variantplaner -t 8 struct -i genotypes/samples/*.parquet -- genotypes -p genotypes/partitions


# Add annotations:
# MEMO: With Annovar each annot is an INFO key -> can reuse original VCF ?
#       -> but 1st remove FORMAT ('cut -f1-8'), otherwise vcf2pq keep them
# MEMO2: Could do bellow with 'bcftools annotate', but '-x FORMAT/GT' set entries to '.' without removing
# MEMO3: No need for '-c' if chr len are in VCF header ?
#
bcftools view ../examples/INPUT_hg19_annovar_MPA.vcf.gz |
	cut -f1-8 | bcftools view -Oz -o examples/annovar_MPA.vcf.gz
variantplaner -t 4 vcf2parquet \
	-c grch38.92.csv \
	-i ../examples/annovar_MPA.vcf.gz \
	annotations -o annotations/annovar_MPA.parquet \
	--rename-id annovar_id


# SQL (D = duckDB):

## Compter l'occurrence de chaque variant
D select id id,count(*) from read_parquet('genotypes/samples/*') group by id;

### -> Voir si ça scale
### -> Sinon ne le faire a la volee que pour les variants de la 'view' ('WHERE id==')
### -> Afficher 'chr-pos-ref-alt' plutot que l'id -> JOIN avec 'uniq_variants/chr1.parquet' ?


## Reafficher la table d'origine a partir du lake
### WARN: ca me met les gt,dp etc dans des listes
###       -> Mais je dois pouvoir re-generer en faisant 'sample1:g1, sample2:gt2'
D SELECT s.id,first(COLUMNS(v.*)),first(COLUMNS(a.*)),list(COLUMNS(['sample','gt','dp']) order by sample asc),list(gt order by sample asc) FROM read_parquet('genotypes/samples/*') as s left join read_parquet('uniq_variants/*') as v on s.id=v.id left join read_parquet('annotations/*') as a on s.id=a.id GROUP BY s.id ;
