#!/bin/bash
usage() {
	cat << EOF
USO: [$(dirname $0)/]$(basename $0) [-h]
Soma horarios recebidos via stdin.
Aceita horarios no formatos hh:mm:ss e hh:mm.

OPCOES
-h   Ajuda
EOF
}

# Parse dos argumentos da linha de comando
while getopts "h" OPTION ; do
	case $OPTION in
	h)
		usage
		exit 1
		;;
	?)
		usage
		exit
		;;
	esac
done


# http://unstableme.blogspot.com.br/2009/12/awk-sum-two-times-of-hh-mm-ss-format.html
# http://stackoverflow.com/questions/3096259/bash-command-to-sum-a-column-of-numbers

# return Arr[1] * 3600 + Arr[2] * 60 + Arr[3]
# Troca espacos por \n, para poder aceitar varios horarios na mesma linha, separados por espacos
V_SUM_SECONDS=$(cat | sed 's/ /\n/g' | awk '
function convert_hms_to_seconds( time_hms ) {
	split( time_hms , piece , ":" )
	return piece[1] * 3600 + piece[2] * 60 + piece[3]
}
{ print convert_hms_to_seconds( $1 ) }
' | paste -sd+ - | bc)

# http://unstableme.blogspot.com.br/2009/01/convert-seconds-to-hour-minute-seconds.html
echo - | awk -v "S=$V_SUM_SECONDS" '{ printf "%02d:%02d:%02d\n" , S / ( 60 * 60 ) , S % ( 60 * 60 ) / 60 , S % 60 }'
