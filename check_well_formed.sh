for file in `find ./manuscript_downloads -name '*.xml'`
do 
    xmllint --noout $file
done