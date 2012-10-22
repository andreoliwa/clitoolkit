#!/bin/bash
function usage() {
	cat << EOF
Uso: $(basename $0) [-hancdfjpvw]
Script unico para todos os backups.

Opcoes:
-n   Dry-run
-a   Todas as opcoes abaixo
-c   Configuracao (backup-config.sh)
-d   Deja-dup
-f   Codigo fonte
-j   Jaque
-p   Fotos (diretorio /pix)
-v   Videos
-w   Windows 7
-h   Mostra esta ajuda
EOF
	exit $1
}

# Parse dos argumentos da linha de comando
V_DRY_RUN=
V_ALL=
V_CONFIG=
V_DEJA_DUP=
V_CODE=
V_VIDEOS=
V_WINDOWS=
V_SOMETHING_CHOSEN=
V_JAQUE=
V_PIX=
while getopts "nancdfvwjph" OPTION
do
	case $OPTION in
	n)	V_DRY_RUN=-n ;;
	a)	V_SOMETHING_CHOSEN=1 ; V_ALL=1 ;;
	c)	V_SOMETHING_CHOSEN=1 ; V_CONFIG=1 ;;
	d)	V_SOMETHING_CHOSEN=1 ; V_DEJA_DUP=1 ;;
	f)	V_SOMETHING_CHOSEN=1 ; V_CODE=1 ;;
	v)	V_SOMETHING_CHOSEN=1 ; V_VIDEOS=1 ;;
	w)	V_SOMETHING_CHOSEN=1 ; V_WINDOWS=1 ;;
	j)	V_SOMETHING_CHOSEN=1 ; V_JAQUE=1 ;;
	p)	V_SOMETHING_CHOSEN=1 ; V_PIX=1 ;;
	h)	usage 1 ;;
	?)	usage 2 ;;
	esac
done
if [ -z $V_SOMETHING_CHOSEN ] ; then
	usage 3
fi

if [ -n "$V_DRY_RUN" ] ; then
	echo "Modo simulacao (dry-run)"
fi

if [ -n "$V_ALL" ] || [ -n "$V_CONFIG" ] ; then
	~/bin/backup-config.sh
fi

V_LINUX_VERSION=$(lsb_release -d -s | sed 's/ /-/g')
V_BACKUP_EXTERNAL_DIR=/media/black-samsung-1tb/.backup/linux
if [ -d $V_BACKUP_EXTERNAL_DIR ] ; then
	V_BACKUP_EXTERNAL_DIR=$V_BACKUP_EXTERNAL_DIR/$HOSTNAME-$V_LINUX_VERSION
	mkdir -p $V_BACKUP_EXTERNAL_DIR
else
	echo "Diretorio externo de backup nao encontrado: $V_BACKUP_EXTERNAL_DIR"
fi

if [ -n "$V_ALL" ] || [ -n "$V_DEJA_DUP" ] ; then
	if [ -d $V_BACKUP_EXTERNAL_DIR ] ; then
		echo "Syncing /var/backups/$HOSTNAME/ to $V_BACKUP_EXTERNAL_DIR/"
		if [ -d $V_BACKUP_EXTERNAL_DIR ] ; then
			rsync -havuzO $V_DRY_RUN --progress --modify-window=2 /var/backups/$HOSTNAME/ $V_BACKUP_EXTERNAL_DIR/
		fi
		echo "Done."
	fi
fi


if [ -n "$V_ALL" ] || [ -n "$V_VIDEOS" ] ; then
	if [ -d $V_BACKUP_EXTERNAL_DIR ] ; then
		echo "Backup dos vídeos Linux (Stanford e afins)"
		rsync -havuzO $V_DRY_RUN --delete --progress --modify-window=2 ~/Videos/ $V_BACKUP_EXTERNAL_DIR/Videos/
	fi
fi

if [ $HOSTNAME = $G_WORK_COMPUTER ] ; then
	if [ -n "$V_ALL" ] || [ -n "$V_CODE" ] ; then
		V_ERROR=
		[ ! -d "$V_BACKUP_EXTERNAL_DIR" ] && V_ERROR=1 && echo "Diretorio nao encontrado: $V_BACKUP_EXTERNAL_DIR"
		[ ! -d "$HOME/src/local/" ] && V_ERROR=1 && echo "Diretorio nao encontrado: $HOME/src/local/"
		if [ -z "$V_ERROR" ] ; then
			#echo 'Backup da documentacao do FolhaPress'
			#V_DIR="$V_BACKUP_EXTERNAL_DIR/doc/folhapress/"
			#echo $V_DIR
			#mkdir -p $V_DIR
			#ls -l "/net/srvrevmac/projetosti/2012/FolhaPress/Visão Específica/*"
			#cp -rvu '/net/srvrevmac/projetosti/2012/FolhaPress/Visão Específica/*' $V_DIR

			echo "Backup do codigo fonte de $HOME/src/local/ para $V_BACKUP_EXTERNAL_DIR/src/"
			rsync $V_DRY_RUN -trOlhDuzv --del --modify-window=2 --progress $HOME/src/local/ $V_BACKUP_EXTERNAL_DIR/src/
			#--exclude=*.pack
		fi
	fi
fi

V_POSSIBLE_BACKUP_DIRS='/media/black-samsung-1tb/.backup /media/samsung-500gb/.backup'
V_BACKUP_DIRS=
for V_DIR in $V_POSSIBLE_BACKUP_DIRS ; do
	if [ -d "$V_DIR" ] ; then
		V_BACKUP_DIRS="$V_BACKUP_DIRS $V_DIR"
	else
		echo "Diretorio de backup nao encontrado: $V_DIR"
	fi
done

function sync_dir() {
	for V_DESTINATION_DIR in $V_BACKUP_DIRS ; do
		echo
		echo "Backup do diretorio $V_SOURCE_DIR/$1 em $V_DESTINATION_DIR/$1"
		V_SYNC="rsync $V_DRY_RUN -trOlhDuzv --del --modify-window=2 --progress --exclude=lost+found/"
		echo $V_SYNC \"$V_SOURCE_DIR/$1/\" \"$V_DESTINATION_DIR/$1/\"
		mkdir -p "$V_DESTINATION_DIR/$1/"
		$V_SYNC "$V_SOURCE_DIR/$1/" "$V_DESTINATION_DIR/$1/"
	done
}

if [ -n "$V_ALL" ] || [ -n "$V_PIX" ] ; then
	V_SOURCE_DIR=''
	echo "Backup de fotos"
	sync_dir 'pix'
fi

if [ -n "$V_ALL" ] || [ -n "$V_WINDOWS" ] ; then
	V_SOURCE_DIR='/mnt/windows7'
	if [ ! -d "$V_SOURCE_DIR" ] ; then
		echo "Diretorio do Windows nao montado: $V_SOURCE_DIR"
	else
		sync_dir "Users/Public/Documents"
		sync_dir "Users/Public/Pictures"
		sync_dir "Users/Wagner/Documents"
		sync_dir "Users/Wagner/Dropbox"
		sync_dir "Users/Wagner/Favorites"
		sync_dir "Users/Wagner/Music"
		sync_dir "Users/Wagner/Pictures"
		sync_dir "Users/Wagner/Videos"
	fi
fi

if [ -n "$V_JAQUE" ] ; then
	V_SOURCE_DIR='/media/OS'
	if [ ! -d "$V_SOURCE_DIR" ] ; then
		echo "Diretorio do Windows (Jaque) nao montado: $V_SOURCE_DIR"
	else
		sync_dir "Users/Public/Documents"
		sync_dir "Users/Public/Music"
		sync_dir "Users/Public/Pictures"
		sync_dir "Users/Public/Videos"

		sync_dir "Users/Jaqueline/Desktop"
		sync_dir "Users/Jaqueline/Documents"
		sync_dir "Users/Jaqueline/Downloads"
		sync_dir "Users/Jaqueline/Favorites"
		sync_dir "Users/Jaqueline/Music"
		sync_dir "Users/Jaqueline/Pictures"
		sync_dir "Users/Jaqueline/Videos"
	fi
fi

# MY_EXCLUDE_FILE=~/bin/backup-full-exclude.txt
# MY_CURRENT_DATE=$(date +%Y-%m-%d_%H%M)
# MY_BACKUP_FILE=/var/backups/$HOSTNAME/backup-wagner-incremental-$MY_CURRENT_DATE.tar.gz
# mkdir -p /var/backups/$HOSTNAME
# chmod a+w /var/backups/$HOSTNAME
# #tar -czv $* --listed-incremental=/var/log/wagner-tar-snapshot.snar --preserve-permissions --seek --exclude-from $MY_EXCLUDE_FILE -f $MY_BACKUP_FILE $HOME/
# tar -czv $* --listed-incremental=/var/log/wagner-tar-snapshot.snar --preserve-permissions --seek --exclude-from $MY_EXCLUDE_FILE - $HOME/ | split -b 1000m - $MY_BACKUP_FILE
